'''
Расчет оптимальных зон обслуживания
'''

import pandas as pd
import geopandas as gpd
import networkx as nx
import osmnx as ox


def voronoi_forest(G, sources, path_function, cutoff=None, weight='travel_time', routes_return=False):
    '''
    Расчет Леса Вороного.
    Алгоритм расчета времен прибытия первого подразделения в узлы графа.

    # Аргументы
    `G`: nx.MultiDiGraph
        Граф улично-дорожной сети.
    `sources`:list|dict
        Стартовые узлы. Может быть списком узлов вида list(int), или словарем вида dict(int:str), где ключ - 
        идентификатор узла, значение - его наименование. Может использоваться для указания узлов в которых 
        расположены пожарные подразделения: {1234:'ПСЧ-1'}
    `path_function`: function
        Функция расчета кратчайших путей от единственного источника. 
        В качестве функции могут быть переданы реализации алгоритмов из пакета
        `networkx`. Например, реализация алгоритма Дейкстры: `nx.multi_source_dijkstra`.
        Пользователь может использовать собственные функции с
        интерфейсом `func(G: Graph, sources: Any, target: Any | None = None, cutoff: Any | None = None, 
        weight: str = "weight") -> (dict, dict)`
    `cutoff`:int=None
        Ограничение расчета
    `weight`:str или function  = "travel_time"
        Имя поля содержащего вес ребер, или функция позволяющая вычислять 
        вес динамически.
    `routes_return`: bool = False
        Возвращать ли также и маршруты следования
    '''

    # Расчет
    times, routes = path_function(G, sources=sources, cutoff=cutoff, weight=weight)
    times = pd.Series(times, dtype=float)

    # Определение стартового узла для каждого маршрута
    if isinstance(sources, dict):
        nearest = pd.Series({k:sources[route[0]] for k, route in routes.items()}, dtype=str)
    else:
        nearest = pd.Series({k:route[0] for k, route in routes.items()}, dtype='int64')

    # Построение леса
    # times_forest = {s:{k:v} for s,k,v in zip(nearest, times.items())}

    if routes_return:
        routes = pd.Series(routes)
        return nearest, times, routes
    else:
        return nearest, times


def voronoi_forest_for_points(points, **kwargs):
    '''
    Расчет леса Вороного и возвращение значений для узлов points

    # Аргументы
    `points`: list(int)
        Список точек значения для которых должны быть возвращены.
    `**kwargs`:
        Аргументы функции `voronoi_forest`

    # Возвращает
        [nearest, times], [nearest, times, routes]:
        `nearest`:dict - словарь значений ближайших к текущему узлу стартовых узлов
        `times`:dict - словарь значений времени следования в каждый из узлов
        `routes`:dict - словарь маршрутов следования в каждый из узлов
    '''
    if not isinstance(points, list):
        raise TypeError(f'Аргумент `points` должен иметь тип `list`! Имеет {type(points)}')

    results = voronoi_forest(**kwargs)

    r_out=[]
    for r in results:
        val = dict(filter( lambda x: x[0] in points, r.items()) )
        r_out.append(pd.Series(val))
    return r_out


def voronoi_forest_for_area(area:gpd.GeoDataFrame, **kwargs):
    '''
    Расчет леса Вороного и возвращение значений для набора геоданных area

    # Аргументы
    `area`:gpd.GeoDataFrame
        Геодатафрейм содержащий полигоны границ области. 
        
        Важно! Геодатафрейм должен содержать строго 1 запись!
    `**kwargs`:
        Аргументы функции `voronoi_forest`

    # Возвращает
        [nearest, times], [nearest, times, routes]:
        `nearest`:dict - словарь значений ближайших к текущему узлу стартовых узлов
        `times`:dict - словарь значений времени следования в каждый из узлов
        `routes`:dict - словарь маршрутов следования в каждый из узлов
    '''

    if not len(area)==1:
        raise ValueError(f'В наборе геоданных `area` должно содержаться строго 1 запись! Содержится {len(area)}!')

    try:
        G = kwargs['G']
    except Exception as exc:
        raise TypeError(
            exc
            ) from exc

    if not area.crs == G.graph.get('crs'):
        raise ValueError(f'Системы координат полигона `area` ({area.crs}) и `графа` G ({G.graph.get("crs")}) не совпадают!')

    nodes = ox.graph_to_gdfs(G, edges=False)
    points = nodes[nodes.within(area.iloc[0].geometry)]
    points = list(points.index)

    return voronoi_forest_for_points(points=points, **kwargs)


