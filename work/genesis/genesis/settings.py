'''
Глобальные настройки системы, которые могут быть изменены пользователем

`single_source_forward_path_length`: алгоритм прямого расчета времени прибытия 
    во все узлы графа от единого источника.
`multy_source_forward_path_length`: алгоритм прямого расчета времени прибытия 
    во все узлы графа от множества источников.
'''

import networkx as nx

single_source_forward_path_length = nx.single_source_dijkstra_path_length
multy_source_forward_path_length = nx.multi_source_dijkstra_path_length