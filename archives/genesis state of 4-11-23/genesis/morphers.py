'''
Функции изменяющие модели. Например, добавляющие новые поля данных, вычисляющие их и т.д.
'''

# import networkx as nx
import geopandas as gpd
# from genesis.tools import kmh_to_mm
from genesis.models import SpatialFeature
from genesis.features import RoadNetworkGraph, SpeedProfile
import osmnx as ox
import pandas as pd
import geopandas as gpd
import logging as lg

class MorphersGraph(object):
    '''
    Морферы ГДС
    '''
    @staticmethod
    def add_edge_travel_times(G:RoadNetworkGraph,
                              SP: SpeedProfile,
                              def_speed = 5):
        '''
        Добавляет параметр времени следования для всех ребер ГДС
        '''
        # speed_profile = {k: kmh_to_mm(v) for k,v in speed_profile.items()}

        for edge in G.edges:
            road = G.get_edge_data(*edge).get('highway')
            length = G.get_edge_data(*edge).get('length')
            try:
                # speed = speed_profile.get(road, def_speed)
                speed = SP[road]
            except TypeError: # Тип дороги бывает списком, обычно ['residential', 'сервис']
                if isinstance(road, list):
                    # speed = speed_profile.get(road, def_speed)
                    speed = SP[road]
                else:
                    speed = def_speed

            G.add_edge(*edge, travel_time=length/speed)

    @staticmethod
    def add_edge_speed(G:RoadNetworkGraph,
                              SP: SpeedProfile,
                              def_speed = 5):
        pass

class MorphersSpatialFeature(object):
    '''
    Морферы ПД
    '''
    @staticmethod
    def add_nearest_node(spatial_feature: SpatialFeature,
                         RNG: RoadNetworkGraph,
                         node_field: str = 'node',
                         max_dist:int = 1000):
        '''Добавляет поле содержащее ID ближайшего узла ГДС

        Аргументы
        ---------
        `spatial_feature`: SpatialFeature
            Модель пространственных данных
        `RNG`: RoadNetworkGraph
            Модель графа дорожной сети
        `node_field`: str = 'node'
            Имя поля для сохранения id ближайшего узла ГДС
        `max_dist`:int = 1000
            Максимально допустимое расстояние до узлов ГДС
        '''

        if not isinstance(spatial_feature.data, gpd.GeoDataFrame):
            raise TypeError("Носимые данные spatial_feature должны иметь тип gpd.GeoDataFrame!")
        if not isinstance(RNG, RoadNetworkGraph):
            raise TypeError("Аргумент RNG должен быть строго типа RoadNetworkGraph!")
        if not spatial_feature.crs == RNG.crs:
            raise AssertionError("СК spatial_feature и RNG должны совпадать. В реальности: {spatial_feature.crs} против {RNG.crs}")

        unit_nodes, distance_to_unit = ox.distance.nearest_nodes(RNG.G, spatial_feature.data.geometry.x, spatial_feature.data.geometry.y, return_dist=True)
        for unit, node, distance in zip(spatial_feature.data.index, unit_nodes, distance_to_unit):
            if distance>max_dist:
                print(f'\nРасстояние от ближайшей точки ГДС до подразделения {unit} составляет \
                      {distance} м, что превышает {max_dist} м. \
                    Данное подразделение не будет включено в профиль дислокации \
                    для дальнейшего расчета, так как это влечет потенциальную критическую неточность')
                spatial_feature.data = spatial_feature.data.drop(unit)
            else:
                spatial_feature.data.loc[unit, node_field] = node
        if len(spatial_feature.data)==0:
            lg.debug('Ни одно подразделение не может быть соотнесено с узлами ГДС')
        else:
            spatial_feature.data[node_field]=spatial_feature.data[node_field].astype('int64')
