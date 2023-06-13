'''
Функции изменяющие модели. Например, добавляющие новые поля данных, вычисляющие их и т.д.
'''

import networkx as nx
from tools import kmh_to_mm
from models import RoadNetworkGraph
# import osmnx as ox

class Morphers_graph(object):
    '''
    Морферы ГДС
    '''
    @staticmethod
    def add_edge_travel_times(G:RoadNetworkGraph,
                              speed_profile:dict,
                              def_speed = 5):
        '''
        Добавляет параметр времени следования для всех ребер ГДС
        '''
        speed_profile = {k: kmh_to_mm(v) for k,v in speed_profile.items()}
        for edge in G.edges:
            road = G.get_edge_data(*edge).get('highway')
            length = G.get_edge_data(*edge).get('length')
            try:
                speed = speed_profile.get(road, def_speed)
            except TypeError: # Тип дороги бывает списком, обычно ['residential', 'сервис']
                if isinstance(road, list):
                    speed = speed_profile.get(road, def_speed)
                else:
                    speed = def_speed

        G.add_edge(*edge, travel_time=length/speed)
        
    @staticmethod
    def add_edge_speed_profile(G:RoadNetworkGraph,
                              speed_profile,
                              def_speed = 5):
        pass
