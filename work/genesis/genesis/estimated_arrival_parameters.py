'''
Estimated Arrival Parameters Problem - Задача определения ожидаемых параметров реагирования пожарных подразделений

Метрики прибытия пожарных подразделений
'''

import pandas as pd
import geopandas as gpd
import networkx as nx
import osmnx as ox

from genesis.swiss_knife import DELAY_TIME





@staticmethod
def arrival_time(metric_function,
            zero_val=0,
            err_val=None):
    '''
    Базовая функция расчета метрик времени первого подразделения.
    Возвращает значение указанной метрики для набора узлов.
    Может быть использована как интерфейс для разработки более специализированных функций.

    Аргументы
    ---------
    `metric_function`: function
        Целевая функция расчета метрики. 
        В качестве функции могут быть переданы статистические функции пакета numpy,
        такие как `np.max`, `np.mean` и т.д. 
        А т.ж. функция `estimated_arrival_parameters.cover_index`.
        Кроме того пользователь может использовать собственные функции с
        интерфейсом `func(route_times:pd.Series)`

    `zero_val`: float = 0
        Значение которое будет возвращено в случае передачи набора данных `route_times` без элементов.

    `err_val`: float
        Значение которое будет возвращено в случае ошибки


    Возвращает
    ----------
    `metric_val`: float
        Значение целевой метрики

    Пример
    ------


    Переопределение
    ---------------

    `Переписать!`

    
    '''

    def _arrival_time(route_times: pd.Series):
        '''
        Расчет метрики времени прибытия.

        Аргументы
        ---------
        `route_times`:pd.Series
            Серия данных о временах прибытия в некоторые точки - 
            узлы ГДС или здания.
        '''
        if not isinstance(route_times, pd.Series):
            raise TypeError(
                "Аргумент route_times может быть только типа pd.Series"
                )

        # Увеличиваем значение времени следования на значение времени необходимого для обслуживания вызова
        route_times = route_times + DELAY_TIME

        # Расчет
        if len(route_times)==0:
            return zero_val
        
        try:
            val = metric_function(route_times)
            return val
        except Exception as exc:
            raise TypeError(
                f"Функция {metric_function.__name__} здесь не применима. Уточните ее сигнатуру."
                ) from exc

    return _arrival_time




@staticmethod
def cover_index(
            ip_val=10,
            zero_val=0):
    '''
    Расчет индекса прикрытия.

    Аргументы
    ---------
    `ip_val`:int
        Пороговое значение для определения индекса прикрытия.
        Рекомендуется использовать 10 для городских населенных пунктов и 
        20 для сельских.

    `zero_val`: float = 0
        Значение которое будет возвращено в случае передачи набора данных `route_times` без элементов.

    Возвращает
    ----------
    `metric_val`: float
        Значение целевой метрики

    Пример
    ------
    Вызывается как результат выполнения функции с заданными параметрами:

    для расчета ИП-10:
        `calc_ip()` или `calc_ip(ip_val=10)`
    для расчета ИП-20:
        `calc_ip(ip_val=20)`
    '''
    def _cover_index(route_times:pd.Series):
        '''Расчет индекса прикрытия.

        Аргументы
        ---------
        `route_times`:pd.Series
            Серия данных о временах прибытия в узлы ГДС 
            (или вообще произвольных данных о временах прибытия)
        '''
        if not isinstance(route_times, pd.Series):
            raise TypeError(
                "Аргумент route_times может быть только типа pd.Series"
                )

        # Увеличиваем значение времени следования на значение времени необходимого
        # для обслуживания вызова
        route_times = route_times + DELAY_TIME

        # Расчет
        if len(route_times)==0:
            return zero_val
        ip_len = sum(route_times<=ip_val)
        tot_len = len(route_times)
        return 100*ip_len/tot_len

    return _cover_index




def nodes_metric(G, sources, path_function, metric_function, voronoi_function, cutoff=None, weight='travel_time', **kwargs):
    '''
    Расчет метрики `metric_function` при старте из узлов(а) `sources`.

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
    `metric_function`: function
        Функция расчета метрики. 
        В качестве функции могут быть переданы статистические функции пакета numpy,
        такие как `np.max`, `np.mean` и т.д. 
        А т.ж. функции из модуля `estimated_arrival_parameters`.
        Кроме того пользователь может использовать собственные функции с
        интерфейсом `func(route_times:pd.Series)`
    `voronoi_function`: function
        Функция построения леса Вороного. Рекомендуется использовать функции `voronoi_forest` из
        модуля `optimal_service_areas`
    `cutoff`:int=None
        Ограничение расчета
    `weight`:str или function  = "travel_time"
        Имя поля содержащего вес ребер, или функция позволяющая вычислять 
        вес динамически.
    '''
    _, times = voronoi_function(G=G, sources=sources, path_function=path_function, cutoff=cutoff, weight=weight, **kwargs)
    return metric_function(times)