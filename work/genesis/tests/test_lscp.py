'''
Тесты для расчетов LSCP

`pytest tests/test_lscp.py -s`
'''

import pytest

import numpy as np
import osmnx as ox
import networkx as nx
import pandas as pd
import geopandas as gpd

from genesis.best_points import BestNodeHillClimbing
from genesis.lscp import LSCPCommon
from genesis.states import FirstArrivalUnitState
from genesis.metrics import ArrivalTime, CoverIndex
from genesis.mclp import BestNodesKoptG, BestNodesGA, BestNodesSA
from genesis.stop_cases import ItersStopCase
from genesis.point_selectors import GenesisNodeSelector, RandomNodesSelector, FarNodeSelector




@pytest.fixture(scope='module')
def load_G():
    return ox.load_graphml("tests/data/test_rng.ml")

@pytest.fixture(scope='module')
def load_area():
    return gpd.read_file("tests/data/test_polygon.gpkg")

@pytest.fixture(scope='module')
def load_G_simplyfied():
    G = ox.load_graphml("tests/data/test_rng.ml")
    return ox.simplify_graph(G)

class TestLSCPCommon:
    '''
    Тесты для LSCPCommon
    '''
    def test_lscp(self, load_G_simplyfied):
        '''
        Базовый тест работоспособности
        '''
        G = load_G_simplyfied

        nodes = list(G.nodes())
        existed_units = {nodes[100]: 'A',
                nodes[200]: 'B',
                }
        new_units = {nodes[300]: 'c',
                    nodes[400]: 'd'}

        # Функция расчета лучшего узла в графе
        BNHC = BestNodeHillClimbing(state_function = FirstArrivalUnitState(),
                                    metric_function = ArrivalTime())
        # Функция расчета лучшего размещения заданных узлов
        BNG = BestNodesKoptG(state_function = FirstArrivalUnitState(),
                            metric_function = ArrivalTime(),
                            best_point_function = BNHC,
                            iterations = 5,
                            )
        # Критерий остановки
        stop_case = ItersStopCase(max_iter_count = 2)
        # Селектор следующей точки
        point_selector = GenesisNodeSelector(state_function = FirstArrivalUnitState(),
                                            metric_function = ArrivalTime())


        # Сборка алгоритма
        genesis = LSCPCommon(mclp_function = BNG,
                            point_selector = point_selector,
                            stop_case_function = stop_case,
                            metric_function = ArrivalTime(),
                            start_names_index = 5,
                            names_pattern='ПСЧ {}',
                            )

        # Расчет только динамические узлы
        best_dynamic_nodes, best_metric = genesis(env = G,
                                        dynamic_nodes = new_units,
                                        )
        assert best_dynamic_nodes == {1577701962: 'c', 2042076918: 'd', 290700365: 'ПСЧ 5', 2034401723: 'ПСЧ 6'}
        assert best_metric  ==  4.47569295393134

        # Расчет динамические и статические узлы
        best_dynamic_nodes, best_metric = genesis(env = G,
                                        dynamic_nodes = new_units,
                                        static_nodes = existed_units,
                                        )
        assert best_dynamic_nodes == {2034401275: 'c', 2042076918: 'd', 290700365: 'ПСЧ 5', 2034401894: 'ПСЧ 6'}
        assert best_metric  ==  4.392374431672204

    def test_lscp_empty_dinamic_nodes(self, load_G_simplyfied):
        '''
        Расчет с пустым списком динамических узлов
        '''
        G = load_G_simplyfied

        # Функция расчета лучшего узла в графе
        BNHC = BestNodeHillClimbing(state_function = FirstArrivalUnitState(),
                                    metric_function = ArrivalTime())
        # Функция расчета лучшего размещения заданных узлов
        BNG = BestNodesKoptG(state_function = FirstArrivalUnitState(),
                            metric_function = ArrivalTime(),
                            best_point_function = BNHC,
                            iterations = 5,
                            )
        # Критерий остановки
        stop_case = ItersStopCase(max_iter_count = 2)
        # Селектор следующей точки
        point_selector = GenesisNodeSelector(state_function = FirstArrivalUnitState(),
                                            metric_function = ArrivalTime())


        # Сборка алгоритма
        genesis = LSCPCommon(mclp_function = BNG,
                            point_selector = point_selector,
                            stop_case_function = stop_case,
                            metric_function = ArrivalTime(),
                            start_names_index = 5,
                            names_pattern='ПСЧ {}',
                            )

        # Тест расчета при пустом словаре
        with pytest.raises(ValueError):
            genesis(env = G,
                    dynamic_nodes = {},
                    )

    def test_lscp_area(self, load_G_simplyfied, load_area):
        '''
        Расчет в пределах area
        '''
        G = load_G_simplyfied
        area = load_area

        nodes = list(G.nodes())
        existed_units = {nodes[100]: 'A',
                nodes[200]: 'B',
                }
        new_units = {nodes[300]: 'c',
                    nodes[400]: 'd'}
        
        g_nodes_gdf = ox.graph_to_gdfs(G, edges=False)
        points_mask = g_nodes_gdf.within(area.iloc[0].geometry)

        # Функция расчета лучшего узла в графе
        BNHC = BestNodeHillClimbing(state_function = FirstArrivalUnitState(),
                                    metric_function = ArrivalTime())
        # Функция расчета лучшего размещения заданных узлов
        BNG = BestNodesKoptG(state_function = FirstArrivalUnitState(),
                            metric_function = ArrivalTime(),
                            best_point_function = BNHC,
                            iterations = 5,
                            )
        # Критерий остановки
        stop_case = ItersStopCase(max_iter_count = 2)
        # Селектор следующей точки
        point_selector = GenesisNodeSelector(state_function = FirstArrivalUnitState(),
                                            metric_function = ArrivalTime())

        # Сборка алгоритма
        genesis = LSCPCommon(mclp_function = BNG,
                            point_selector = point_selector,
                            stop_case_function = stop_case,
                            metric_function = ArrivalTime(),
                            start_names_index = 10,
                            names_pattern='ПЧ {}',
                            )

        # Расчет только динамические узлы
        best_dynamic_nodes, best_metric = genesis(env = G,
                                        dynamic_nodes = new_units,
                                        static_nodes = existed_units,
                                        area = points_mask
                                        )
        assert best_dynamic_nodes == {2034401275: 'c', 9774067520: 'd', 2034401650: 'ПЧ 10', 426923846: 'ПЧ 11'}
        assert best_metric  ==  2.5924815766972755


    def test_lscp_GA(self, load_G_simplyfied):
        '''
        расчет для ГА
        '''
        G = load_G_simplyfied

        nodes = list(G.nodes())
        existed_units = {nodes[100]: 'A',
                nodes[200]: 'B',
                }
        new_units = {nodes[300]: 'c',
                    nodes[400]: 'd'}

        # Функция расчета лучшего размещения заданных узлов
        BNGA = BestNodesGA(state_function = FirstArrivalUnitState(),
                            metric_function = ArrivalTime(),
                            node_selector = RandomNodesSelector(),
                            population_size=20,
                            epochs = 3,
                            )
        # Критерий остановки
        stop_case = ItersStopCase(max_iter_count = 2)
        # Селектор следующей точки
        point_selector = FarNodeSelector(FirstArrivalUnitState())


        # Сборка алгоритма
        genesis = LSCPCommon(mclp_function = BNGA,
                            point_selector = point_selector,
                            stop_case_function = stop_case,
                            metric_function = ArrivalTime(),
                            start_names_index = 5,
                            names_pattern='ПСЧ {}',
                            )

        # Расчет только динамические узлы
        best_dynamic_nodes, best_metric = genesis(env = G,
                                        dynamic_nodes = new_units,
                                        static_nodes = existed_units,
                                        )
        assert len(best_dynamic_nodes) == 4
        assert best_metric  <  5


    def test_lscp_SA(self, load_G_simplyfied):
        '''
        расчет для ИО
        '''
        G = load_G_simplyfied

        nodes = list(G.nodes())
        # existed_units = {nodes[100]: 'A',
        #         nodes[200]: 'B',
        #         }
        new_units = {nodes[200]: 'c',
                    nodes[500]: 'd'}

        # Функция расчета лучшего размещения заданных узлов
        BNSA = BestNodesSA(state_function = FirstArrivalUnitState(),
                            metric_function = ArrivalTime(),
                            node_selector = RandomNodesSelector(),
                            end_temperature = 0.01
                            )
        # Критерий остановки
        stop_case = ItersStopCase(max_iter_count = 4)
        # Селектор следующей точки
        point_selector = FarNodeSelector(FirstArrivalUnitState())


        # Сборка алгоритма
        genesis = LSCPCommon(mclp_function = BNSA,
                            point_selector = point_selector,
                            stop_case_function = stop_case,
                            metric_function = ArrivalTime(),
                            start_names_index = 5,
                            names_pattern='ПСЧ {}',
                            )

        # Расчет только динамические узлы
        best_dynamic_nodes, best_metric = genesis(env = G,
                                        dynamic_nodes = new_units,
                                        # static_nodes = existed_units,
                                        )
        assert len(best_dynamic_nodes) == 6
        assert best_metric  <  4

