'''
Функции расчета метрик ГДС
'''

import networkx as nx
from settings import *

def metric_calc(G:nx.MultiDiGraph, node:int, func=None, weight: str = "weight"):
    '''
    Возвращает значение стандартной целевой метрики.

    Аргументы
    ---------
    `G`:nx.MultiDiGraph, 
        Граф дорожной сети
    
    `node`:int
        Узел для которого производится расчет

    `func`: function
        Целевая функция расчета метрики. По-умолчанию - max.
    
    `weight`:str или function
        Имя поля содержащего вес ребер, или функция позволяющая вычислять вес динамически.

    Возвращает
    ----------
    `metric_val`: float
        Значение целевой метрики
    '''
    if not isinstance(G, nx.MultiDiGraph):
        raise TypeError("Аргумент G должен быть мультиграфом!") 
    if not isinstance(node, int):
        raise TypeError("Идентификатор узла должен иметь тип данных int!")
    if not node in G.nodes():
        raise Exception(f"Узел {node} отсутствует в графе G")
    
    # route_lens = nx.single_source_dijkstra_path_length(G, node, weight=weight)
    # route_lens = settings.single_source_forward_path_length(G, node, weight=weight)
    route_lens = single_source_forward_path_length(G, node, weight=weight)   

    if func==None:
        return max(route_lens.values())
    else:
        return func(route_lens.values())


def max_time(G:nx.MultiDiGraph, node:int, weight: str = "weight"):
    '''
    Возвращает протяженность маршрута от заданного узла до наиболее удаленного от нее

    Аргументы
    ---------
    `G`:nx.MultiDiGraph, 
        Граф дорожной сети
    
    `node`:int
        Узел для которого производится расчет

    `weight`:str или function
        Имя поля содержащего вес ребер, или функция позволяющая вычислять вес динамически.

    Возвращает
    ----------
    `max_time`: float
        Протяженность маршрута от заданного узла до наиболее удаленного от нее, 
        с учетом веса ребер маршрута
    '''
    return metric_calc(G, node, weight=weight)