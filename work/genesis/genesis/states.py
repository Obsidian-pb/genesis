'''
Расчет оптимальных зон обслуживания
'''

import pandas as pd
import geopandas as gpd
import networkx as nx
import osmnx as ox

from genesis.core import StateBase
from genesis.swiss_knife import DELAY_TIME, MSF


class FirstArrivalUnitState(StateBase):
    def __init__(self, state_algorithm=MSF, **kwargs):
        '''
            `state_algorithm`: function
            Функция расчета кратчайших путей от единственного источника. 
            В качестве функции могут быть переданы реализации алгоритмов из пакета
            `networkx`. Например, реализация алгоритма Дейкстры: `nx.multi_source_dijkstra`.
            Пользователь может использовать собственные функции с
            интерфейсом `func(G: Graph, sources: Any, target: Any | None = None, cutoff: Any | None = None, 
            weight: str = "weight") -> (dict, dict)`
        '''
        # self.state_algorithm = state_algorithm
        super().__init__(state_algorithm, **kwargs)

    def __call__(self, env, points, area=None, weight='travel_time', delay=DELAY_TIME, **kwargs):
        '''
        # Аргументы
        `env`: nx.MultiDiGraph (G)
            Граф улично-дорожной сети.
        `points`: list|dict (source)
            Стартовые узлы. Может быть списком узлов вида list(int), или словарем вида dict(int:str), где ключ - 
            идентификатор узла, значение - его наименование. Может использоваться для указания узлов в которых 
            расположены пожарные подразделения: {1234:'ПСЧ-1'}
        `area`: pd.Series = None
            Маска узлов графа. Значениями True отмечены узлы графа - цели расчета леса Вороного.
            Если не указана, расчет производится для всех узлов графа.
        `weight`:str или function  = "travel_time"
            Имя поля содержащего вес ребер, или функция позволяющая вычислять 
            вес динамически.
        `delay`: 
            Задержка в расчете. Например на обслуживание вызова на пожар.
            По умолчанию указана в swiss_knife.DELAY_TIME

        # Возвращает
            times, nearest -> tuple[Series[float], Series[str] | Series]. 
            times - Время прибытия первого подразделения в каждый из узлов графа. 
            nearest - Соответствие узлов первому подразделению. 
        '''

        if not isinstance(env, nx.MultiDiGraph):
            raise TypeError('Тип данных аргумента `env` должен быть nx.MultiDiGraph')
        if not isinstance(points, (list, dict)):
            raise TypeError('Тип данных аргумента `points` должен быть (list или dict)')
        if not area is None and not isinstance(area, pd.Series):
            raise TypeError(f'Аргумент `area` должен иметь тип `list`! Имеет {type(area)}')

        # Расчет
        times, routes = self.state_algorithm(G=env, sources=points, weight=weight, **kwargs)
        times = pd.Series(times, dtype=float, name='route_time') + delay

        # Определение стартового узла для каждого маршрута
        if isinstance(points, dict):
            nearest = pd.Series({k:points[route[0]] for k, route in routes.items()}, dtype=str, name='first_arrival_unit')
        else:
            nearest = pd.Series({k:route[0] for k, route in routes.items()}, dtype='int64', name='first_arrival_unit')

        # Отбор узлов по маске
        if not area is None:
            times = times[area]
            nearest = nearest[area]

        # Построение леса. Потом удалить.
        # times_forest = {s:{k:v} for s,k,v in zip(nearest, times.items())}

        return times, nearest
