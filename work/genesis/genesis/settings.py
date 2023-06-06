'''
Глобальные настройки системы, которые могут быть изменены пользователем

## Functions
`single_source_forward_path_length (ssfpl)`: алгоритм прямого расчета времени прибытия 
    во все узлы графа от единого источника.
`multy_source_forward_path_length (msfpl)`: алгоритм прямого расчета времени прибытия 
    во все узлы графа от множества источников.
'''

import networkx as nx

# class Functions(object):
ssfpl = nx.single_source_dijkstra_path_length
msfpl = nx.multi_source_dijkstra_path_length