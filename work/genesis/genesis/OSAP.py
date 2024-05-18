'''
Расчет времен прибытия
'''

import pandas as pd
# import geopandas as gpd
import networkx as nx
# import osmnx as ox


def estimated_arrival_time_first_unit(G,
                           path_function,
                           sources,
                           weight='travel_time',
                           arrival_name='arrival_time',
                           nearest_name = 'nearest',
                           add_time=1,
                           cutoff=None):
    '''
    Алгоритм расчета времен прибытия первого подразделения в узлы графа из ближайшего стартового узла.

    # Аргументы
    `G`: nx.MultiDiGraph
        Граф улично-дорожной сети.
    `path_function`: function
        Функция расчета кратчайших путей от единственного источника. 
        В качестве функции могут быть переданы реализации алгоритмов из пакета
        `networkx`. Например, реализация алгоритма Дейкстры: `nx.multi_source_dijkstra`.
        Пользователь может использовать собственные функции с
        интерфейсом `func(G: Graph, sources: Any, target: Any | None = None, cutoff: Any | None = None, 
        weight: str = "weight") -> (dict, dict)`
    `sources`:list|dict
        Стартовые узлы. Может быть списком узлов вида list(int), или словарем вида dict(int:str), где ключ - 
        идентификатор узла, значение - его наименование. Может использоваться для указания узлов в которых 
        расположены пожарные подразделения: {1234:'ПСЧ-1'}
    `weight`:str или function  = "travel_time"
        Имя поля содержащего вес ребер, или функция позволяющая вычислять 
        вес динамически.
    `arrival_name`:str='arrival_time'
        Имя атрибута в котором будет сохранено время прибытия в узел
    `nearest_name` = 'nearest'
        Имя атрибута в котором будет сохранен идентификатор ближайшего стартового узла
    `add_time`: float
        Дополнительное время для учета при расчете итогового времени прибытия.
        Например, время для обработки сообщения.
    `cutoff`:int=None
        Ограничение расчета
    '''

    # Проверка типов входящих данных
    if isinstance(sources, list):
        if isinstance(sources, list):
            if len(sources)==0:
                raise ValueError('В sources нет ни одного элемента!')
            for element in sources:
                if not isinstance(element, int):
                    raise TypeError("Все идентификаторы узлов в списке sources должны иметь тип данных int!")
                if not element in G.nodes():
                    raise KeyError(f"Узел {element} отсутствует в графе G")
    elif isinstance(sources, dict):
        if len(sources)==0:
            raise ValueError('В sources нет ни одного элемента!')
        for node, name in sources.items():
            if not isinstance(name, str):
                raise TypeError("Все имена узлов в словаре sources должны иметь тип данных str!")
            if not node in G.nodes():
                raise KeyError(f"Узел {node} отсутствует в графе G")
    else:
        raise TypeError("Идентификатор узла должен иметь тип данных int или list(int)!")
    if not isinstance(G, nx.MultiDiGraph):
        raise TypeError("Аргумент G должен иметь тип nx.MultiDiGraph!")


    # Расчет леса Вороного
    times, routes = path_function(G, sources=sources, cutoff=cutoff, weight=weight)

    # Формирование итоговых серий. Сопоставление со стартовыми точками. Разделение на зоны обслуживания.
    times = pd.Series(times)+add_time
    if isinstance(sources, dict):
        nearest = pd.Series({k:sources[route[0]] for k, route in routes.items()}, dtype=str)
    else:
        nearest = pd.Series({k:route[0] for k, route in routes.items()}, dtype='int64')

    # Установка результатов расчета в качестве атрибутов ребер
    nx.set_node_attributes(G, times, arrival_name)
    nx.set_node_attributes(G, nearest, nearest_name)