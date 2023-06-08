'''
Функции изменяющие модели. Например, добавляющие новые поля данных, вычисляющие их и т.д.
'''

import networkx as nx
# import osmnx as ox

class Morphers_graph(object):
    '''
    Морферы ГДС
    '''
    @staticmethod
    def add_edge_travel_times(G:nx.MultiDiGraph, 
                              speed_profile, 
                              def_speed = 5):
        pass
        

