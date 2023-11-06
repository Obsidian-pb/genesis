'''
Инструменты обработки графов, моделей и данных. Обрезка, соединение, сохранение, загрузка
'''

import pandas as pd
import geopandas as gpd
import logging as lg


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


def data_frame_to_geo_data_frame(
                                df: pd.DataFrame,
                                nodes_gdf: gpd.GeoDataFrame,
                                index_name='node'):
    '''
    Превращаем объект с типом данных pandas.DataFrame в объект 
    с типом данных pandas.GeoDataFrame

    Аргументы
    ---------
    `df`: pd.DataFrame
        Исходный датафрейм
    `nodes_gdf`: gpd.GeoDataFrame
        Геодатафрейм содержащий геометрию узлов.
        Рекомендуется использовать геодатафрейм узлов ГДС
    `index_name`='node'
        Имя поля индекса в итоговом наборе

    Возвращает
    ----------
    `gdf`: gpd.GeoDataFrame
        Геодатафрейм с геометрией узлов
    '''
    if not isinstance(df, pd.DataFrame):
        raise TypeError('Аргумент df имеет тип данных отличный от pd.DataFrame')
    lg.debug("Добавить проверки на тип данных индекса - узлы ли")

    df_p = pd.concat([
        df,
        pd.Series(nodes_gdf['geometry'], name='geometry'),
        ],
        axis=1,
        join='inner')
    gdf = gpd.GeoDataFrame(df_p).set_crs(nodes_gdf.crs)
    gdf.index.name=index_name
    return gdf

def get_all_neighbour_nodes(G, node):
    nnodes = []
    for edge in G.out_edges(node):
        nnodes.append(edge[1])
    for edge in G.in_edges(node):
        nnodes.append(edge[0])
    return nnodes