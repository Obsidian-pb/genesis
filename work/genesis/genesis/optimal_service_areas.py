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

    if not isinstance(sources, (list, dict)):
        raise TypeError(f'Тип данных аргумента `sources` должен быть (list или dict)')

    # Расчет
    times, routes = path_function(G, sources=sources, cutoff=cutoff, weight=weight)
    times = pd.Series(times, dtype=float, name='route_time')

    # Определение стартового узла для каждого маршрута
    if isinstance(sources, dict):
        nearest = pd.Series({k:sources[route[0]] for k, route in routes.items()}, dtype=str, name='first_arrival_unit')
    else:
        nearest = pd.Series({k:route[0] for k, route in routes.items()}, dtype='int64', name='first_arrival_unit')

    # Построение леса
    # times_forest = {s:{k:v} for s,k,v in zip(nearest, times.items())}

    if routes_return:
        routes = pd.Series(routes)
        return nearest, times, routes
    else:
        return nearest, times


def voronoi_forest_for_points(points, **kwargs):
    '''
    `Не рекомендуется использовать!`

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
    # print('Функция `voronoi_forest_for_points` устарела и будет в последующем заменена, не рекомендуется ее использование')
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
        raise ValueError(f'В наборе геоданных `area` должно содержаться строго 1 запись!' \
                         'Содержится {len(area)}!')

    try:
        G = kwargs['G']
    except Exception as exc:
        raise TypeError(
            exc
            ) from exc

    if not area.crs == G.graph.get('crs'):
        raise ValueError(f'Системы координат полигона `area` ({area.crs}) и `графа` ' \
                         'G ({G.graph.get("crs")}) не совпадают!')

    nodes = ox.graph_to_gdfs(G, edges=False)
    points_mask = nodes.within(area.iloc[0].geometry)

    return voronoi_forest_for_points_mask(points_mask=points_mask, **kwargs)


def voronoi_forest_for_points_mask(points_mask, to_df=False, **kwargs):
    '''
    Расчет леса Вороного и возвращение значений для маски узлов points

    # Аргументы
    `points_mask`: list(int)
        Маска точек значения для которых должны быть возвращены.
    `to_df`: bool
        Если True, то при проведении расчета, данные промежуточно преобразовываются к 
        pd.DataFrame. Скорость расчета несколько увеличивается, но результат остается тем же!
    `**kwargs`:
        Аргументы функции `voronoi_forest`

    # Возвращает
        [nearest, times], [nearest, times, routes]:
        `nearest`:dict - словарь значений ближайших к текущему узлу стартовых узлов
        `times`:dict - словарь значений времени следования в каждый из узлов
        `routes`:dict - словарь маршрутов следования в каждый из узлов
    '''
    # if not isinstance(points_mask, list):
    #     raise TypeError(f'Аргумент `points_mask` должен иметь тип `list`! Имеет {type(points_mask)}')

    results = voronoi_forest(**kwargs)

    if to_df:
        result_names = [r.name for r in results]
        r_out = pd.concat([r.to_frame() for r in results], axis=1).loc[points_mask]
        return [r_out[n] for n in result_names]
    else:
        r_out=[]
        for r in results:
            val = r[points_mask]
            r_out.append(pd.Series(val))
        return r_out

def voronoi_forest_for_points_mask2(points_mask, **kwargs):
    '''
        `НЕ ИСПОЛЬЗОВАТЬ!`

        Частная реадизация voronoi_forest_for_points_mask с предварительным преобразованием к DataFrame
    '''
    return voronoi_forest_for_points_mask(points_mask=points_mask, to_df=True, **kwargs)
