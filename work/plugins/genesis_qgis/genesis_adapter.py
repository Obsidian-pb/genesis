import os
from enum import Enum

import geopandas as gpd
import networkx as nx
import osmnx as ox
from shapely.ops import unary_union

from genesis.metrics import ArrivalTime, CoverIndex
from genesis.states import FirstArrivalUnitState, get_atm
from genesis.mclp import BestNodesKoptG
from genesis.lscp import LSCP_ADD
from genesis.point_selectors import RandomNodesSelector
from genesis.swiss_knife import DELAY_TIME, MSF
from fire_units.metrics import ArrivalTimeBuilding, CoverIndexBuilding
from fire_units.mclp import BestNodesGAKopt
from fire_units.best_points import BestNodeHillClimbingHD
from graphs.speeds import kmh_to_mm, set_graph_travel_times
from graphs.algorithms import graph_rise_from_gpkg


class MetricType(Enum):
    ARRIVAL_TIME = 0
    COVER_INDEX_10 = 1
    COVER_INDEX_20 = 2




class GenesisAdapter:
    """
    Адаптер для работы с библиотеками Genesis, fire_units, graphs.
    Инкапсулирует подготовку графа, создание метрик и запуск расчётов.
    """
    def __init__(self, feedback=None):
        self.feedback = feedback

    def prepare_graph(self,
                      roads_gdf, 
                      speeds, 
                      simplify          = True, 
                      columns_list      = None, 
                      travel_time_field = 'travel_time'):
        if columns_list is None:
            columns_list = ['highway', 'oneway', 'lanes']
        G = graph_rise_from_gpkg(roads_gdf, columns_list=columns_list)
        if simplify:
            G = ox.simplify_graph(G)
        set_graph_travel_times(G, speeds, morph_function=kmh_to_mm, travel_time_field=travel_time_field)
        return G

    def layer_to_gdf(self, layer):
        return gpd.GeoDataFrame.from_features(list(layer.getFeatures()), crs=layer.sourceCrs().authid())

    def create_metric(self, optimized_metric, target_points_gdf=None):
        if target_points_gdf is None:
            if optimized_metric == MetricType.ARRIVAL_TIME:
                return ArrivalTime()
            elif optimized_metric == MetricType.COVER_INDEX_10:
                return CoverIndex()
            elif optimized_metric == MetricType.COVER_INDEX_20:
                return CoverIndex(20)
        else:
            if optimized_metric == MetricType.ARRIVAL_TIME:
                return ArrivalTimeBuilding(target_points_gdf)
            elif optimized_metric == MetricType.COVER_INDEX_10:
                return CoverIndexBuilding(target_points_gdf)
            elif optimized_metric == MetricType.COVER_INDEX_20:
                return CoverIndexBuilding(target_points_gdf, ip_val=20)
        raise ValueError('Неизвестная метрика')

    def run_mclp(self, G, optimized_units_gdf, existed_units_gdf, metric_func, nodes_list, params, area=None, feedback=None):
        # Привязка подразделений к узлам графа
        optimized_units_gdf['node'] = ox.nearest_nodes(G, optimized_units_gdf.geometry.x, optimized_units_gdf.geometry.y)
        optimized_units_dict = dict(zip(optimized_units_gdf['node'], optimized_units_gdf['name']))
        existed_units_dict = None
        if existed_units_gdf is not None:
            existed_units_gdf['node'] = ox.nearest_nodes(G, existed_units_gdf.geometry.x, existed_units_gdf.geometry.y)
            existed_units_dict = dict(zip(existed_units_gdf['node'], existed_units_gdf['name']))

        # Алгоритмы
        bpf = BestNodeHillClimbingHD(FirstArrivalUnitState(), metric_function=metric_func)
        kopt = BestNodesKoptG(FirstArrivalUnitState(), metric_function=metric_func, best_point_function=bpf, iterations=3)
        mclp = BestNodesGAKopt(FirstArrivalUnitState(),
                               metric_function    = metric_func, 
                               kopt_function      = kopt, 
                               node_selector      = RandomNodesSelector(nodes_list=nodes_list), 
                               population_size    = params['population_size'], 
                               epochs             = params['epochs'], 
                               mutation_rate      = params['mutation_rate'], 
                               elite_size         = params['elite_size'], 
                               mutation_max_count = params['mutation_max_count'])

        # Запуск расчёта
        if len(optimized_units_dict) == 1:
            best_nodes, best_metric = kopt(env=G, dynamic_nodes=optimized_units_dict, static_nodes=existed_units_dict, area=area)
        else:
            best_nodes, best_metric = mclp(env=G, dynamic_nodes=optimized_units_dict, static_nodes=existed_units_dict, area=area)
        return best_nodes, best_metric

    def run_blp_add(self,
                    G,
                    # optimized_units_gdf,
                    existed_units_gdf, 
                    metric_func, 
                    nodes_list, 
                    params,
                    target_gdf: gpd.GeoDataFrame = None,
                    area=None, 
                    feedback=None,
                    ):
        """
        Применение алгоритма жадного добавления для расчета 
        оптимального размещения ПСЧ
        """

        # 1. Расчет матрицы прибытия
        matrix = get_atm(G,
            data              = target_gdf,
            data_sample_size  = params['data_sample_size'], 
            data_node_field   = params['data_node_field'],
            weight            = params['weight'],
            cutoff            = params['cutoff'],
            data_cutoff_field = params['data_cutoff_field'],
            delay             = DELAY_TIME,
            target_set        = params['target_set'],
            )
        
        # Выбор алгоритма моделирования параметров прибытия
        state = FirstArrivalUnitState()

        # Функция остановки
        stop_case = lambda dynamic_nodes, **kwargs: len(dynamic_nodes) >= 1      # Расчет проводится для 1 подразделения

        # 2. Сборка и инициализация алгоритма ADD
        add = LSCP_ADD(  
                state_function      = state,
                matrix              = matrix,
                metric_function     = metric_func,
                ip_val              = params['ip_val'],
                # mclp_function: MCLPBase = None,
                # point_selector: PointSelectorBase = None,
                stop_case_function  = stop_case,
                names_pattern       = params['names_pattern'],
                start_names_index   = params['start_names_index'],
                after_mclp_function = feedback,
        )

        ## Формирование словаря подразделений для передачи алгоритму
        units_dict = {k:v for k,v in zip(existed_units_gdf[params['node_field']], 
                                         existed_units_gdf[params['name_field']])}

        # 3. Расчет BLP (применение алгоритма)
        best_nodes, best_metric = add(
                env          = G,
                static_nodes = units_dict,  # Размещение существующих подразделений пожарной охраны
                area         = area,
                nodes_list   = nodes_list,
            )
        
        return best_nodes, best_metric

    