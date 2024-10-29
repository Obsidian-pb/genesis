'''
Инструменты обработки графов, моделей и данных. Обрезка, соединение, сохранение, загрузка
'''

from typing import Any

import time
import pandas as pd
import geopandas as gpd
import logging as lg
import networkx as nx


# Блок простых инструментальных функций общего назначения
# def kmh_to_mm(kmh: float, precision: int = 2) -> float:
#     '''
#     Перевод километров в час в метры в минуту

#     Аргументы
#     ---------
#     `kmh`: float
#         Скорость в километрах в час

#     `precision`: int
#         Точность округления, знаков после запятой

#     Возвращает
#     ----------
#     `mm`: float
#         Скорость в метрах в минуту
#     '''
#     if not isinstance(kmh, (int, float)):
#         raise TypeError("Аргумент kmh должен иметь тип данных int или float")

#     return round(kmh*1000/60, precision)


# def data_frame_to_geo_data_frame(
#                                 df: pd.DataFrame,
#                                 nodes_gdf: gpd.GeoDataFrame,
#                                 index_name='node'):
#     '''
#     Превращаем объект с типом данных pandas.DataFrame в объект 
#     с типом данных pandas.GeoDataFrame

#     Аргументы
#     ---------
#     `df`: pd.DataFrame
#         Исходный датафрейм
#     `nodes_gdf`: gpd.GeoDataFrame
#         Геодатафрейм содержащий геометрию узлов.
#         Рекомендуется использовать геодатафрейм узлов ГДС
#     `index_name`='node'
#         Имя поля индекса в итоговом наборе

#     Возвращает
#     ----------
#     `gdf`: gpd.GeoDataFrame
#         Геодатафрейм с геометрией узлов
#     '''
#     if not isinstance(df, pd.DataFrame):
#         raise TypeError('Аргумент df имеет тип данных отличный от pd.DataFrame')
#     lg.debug("Добавить проверки на тип данных индекса - узлы ли")

#     df_p = pd.concat([
#         df,
#         pd.Series(nodes_gdf['geometry'], name='geometry'),
#         ],
#         axis=1,
#         join='inner')
#     gdf = gpd.GeoDataFrame(df_p).set_crs(nodes_gdf.crs)
#     gdf.index.name=index_name
#     return gdf

def get_all_neighbor_nodes(G, node) -> list:
    '''
    Возвращает полный список всех соседних узлов.
    '''
    nnodes = []
    for edge in G.out_edges(node):
        nnodes.append(edge[1])
    for edge in G.in_edges(node):
        nnodes.append(edge[0])
    return nnodes


def multi_source_dijkstra_reversed(G, sources, **kwargs) -> Any:
    '''
    Алгоритм расчета кратчайших маршрутов в точки `source`
    с использованием алгоритма Дейкстры
    в реализации `nx.multi_source_dijkstra`.
    '''
    G = nx.reverse(G.copy())
    return nx.multi_source_dijkstra(G=G, sources=sources, **kwargs)


def list_dict_concat(a:list|dict,b:list|dict) -> list|dict:
    '''
    Корректно склеивает между собой списки и словари.
    При условии, что аргумент `a` и аргумент `b` одного типа.

    #Аргументы
    `a`, `b`: list|dict
        Аргументы которые следует склеить между собой
    '''
    if isinstance(a,list) and isinstance(b,list):
        return a+b
    elif isinstance(a,dict) and isinstance(b,dict):
        return {**a, **b}
    else:
        raise TypeError(f'Аргументы имеют различный тип данных: {a:type(a)}, {b:type(b)}')

def k_v_dict(d, f=min):
    '''
    Получаем номер ключа в словаре которому соответствует значение с
    минимальным/максимальным/средним и т.д. значением, в зависимости
    от функции f.

    Самый быстрый способ.
    '''
    v=list(d.values())
    k=list(d.keys())
    return k[v.index(f(v))]

def get_dict_key(dictionary, value):
    for key, value_in_dict in dictionary.items():
        if value_in_dict == value:
            return key
    return None

def get_duplicates_list(seq):
    '''
    Получение списка дублирующихся во входящем списке значений
    '''
    duplicates = []
    unique = []
    for s in seq:
        if s not in unique:
            unique.append(s)
        else:
            duplicates.append(s)
    return duplicates
