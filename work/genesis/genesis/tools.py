'''
Инструменты обработки графов, моделей и данных. Обрезка, соединение, сохранение, загрузка
'''

import time
import pandas as pd
import geopandas as gpd
import logging as lg
import networkx as nx


# Блок простых инструментальных функций общего назначения
def kmh_to_mm(kmh: float, precision: int = 2):
    '''
    Перевод километров в час в метры в минуту

    Аргументы
    ---------
    `kmh`: float
        Скорость в километрах в час

    `precision`: int
        Точность округления, знаков после запятой

    Возвращает
    ----------
    `mm`: float
        Скорость в метрах в минуту
    '''
    if not isinstance(kmh, (int, float)):
        raise TypeError("Аргумент kmh должен иметь тип данных int или float")

    return round(kmh*1000/60, precision)


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

def get_all_neighbor_nodes(G, node):
    '''
    Возвращает полный список всех соседних узлов.
    '''
    nnodes = []
    for edge in G.out_edges(node):
        nnodes.append(edge[1])
    for edge in G.in_edges(node):
        nnodes.append(edge[0])
    return nnodes


def multi_source_dijkstra_reversed(G, sources, **kwargs):
    '''
    Алгоритм расчета кратчайших маршрутов в точки `source`
    с использованием алгоритма Дейкстры
    в реализации `nx.multi_source_dijkstra`.
    '''
    G = nx.reverse(G.copy())
    return nx.multi_source_dijkstra(G=G, sources=sources, **kwargs)


def timing(f, msg='', acc=2):
    '''
    Обертка счетчика затраченного времени
    '''
    def _timing(**kwargs):
        # Фиксация стартового времени функции
        st = time.time()

        # Собственно оборачиваемая функция
        r = f(**kwargs)

        # Печать времени работы функции
        ft = time.time()
        if msg == '':
            print(f'ВРЕМЯ: {round(ft-st,acc)} сек')
        else:
            print(f'{msg} {round(ft-st,acc)} сек')
        return r

    return _timing


class Progressbar(object):
    '''
    Прогресс бар для использования в итеративных функциях
    '''
    def __init__(self, maxval, minval=0, bins=10, ok_char='#', est_char='_'):
        self.maxval = maxval
        self.minval = minval
        self.bins = bins
        self.scope = maxval-minval
        self.val=minval
        self.ok_char = ok_char
        self.est_char = est_char

    def __call__(self):
        self.val+=1
        bins_ok = int(self.bins*(self.val/self.scope))
        bins_still = self.bins-bins_ok
        s = "|"+self.ok_char*bins_ok + self.est_char*bins_still + "| " + f'{round(100*self.val/self.scope, 1)}%'
        print(s, end='\r')
        if bins_ok==self.bins:
            print('')

