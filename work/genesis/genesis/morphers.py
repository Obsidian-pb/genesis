'''
Функции изменяющие модели. Например, добавляющие новые поля данных, вычисляющие их и т.д.
'''

import networkx as nx
# from genesis.tools import kmh_to_mm
from genesis.models import RoadNetworkGraph, SpeedProfile, DislocationProfile
import osmnx as ox
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
    def add_edge_speed_profile(G:RoadNetworkGraph,
                              speed_profile,
                              def_speed = 5):
        pass

class MorphersDP(object):
    '''
    Морферы ПД
    '''
    @staticmethod
    def add_nearest_node(DP: DislocationProfile,
                         RNG: RoadNetworkGraph,
                         node_field: str = 'node',
                         max_dist:int = 1000,
                         crs:str = None):
        
        lg.warning("Вынести приведение к единой СК в отдельный морфер")
        # приведение к единой системе координат
        if crs is None:
            # Если конкретная СК не указана используется СК графа
            DP.data = DP.data.to_crs(RNG.data.graph['crs'])
        else:
            # ... иначе устанавливается согласно аргумента crs
            DP.data = DP.data.to_crs(crs)
            RNG.data = ox.project_graph(RNG.G, crs)

        unit_nodes, distance_to_unit = ox.distance.nearest_nodes(RNG.G, DP.data.geometry.x, DP.data.geometry.y, return_dist=True)
        for unit, node, distance in zip(DP.data.index, unit_nodes, distance_to_unit):
            if distance>max_dist:
                print(f'\nРасстояние от ближайшей точки ГДС до подразделения {unit} составляет \
                      {distance} м, что превышает {max_dist} м. \
                    Данное подразделение не будет включено в профиль дислокации \
                    для дальнейшего расчета, так как это влечет потенциальную критическую неточность')
                DP.data = DP.data.drop(unit)
            else:
                DP.data.loc[unit, node_field] = node
        if len(DP.data)==0:
            lg.debug('Ни одно подразделение не может быть соотнесено с узлами ГДС')
        else:
            DP.data[node_field]=DP.data[node_field].astype('int64')

            