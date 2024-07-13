'''
Алгоритмы выбора узлов.
'''


import random

import pandas as pd
import networkx as nx

from genesis.core import MetricBase, PointSelectorBase, StateBase
from genesis.tools import get_dict_key



class RandomNodesSelector(PointSelectorBase):
    '''
    Простой выбор случайного узла в графе
    '''
    def __init__(self, **kwargs) -> None:
        '''
        Простой выбор случайного узла в графе
        '''

    def __call__(self,
                env:nx.MultiDiGraph,
                points:dict,
                area: pd.Series = None,
                k:int = 1,
                **kwargs):
        '''
        Запуск работы алгоритма

        ## Аргументы
        `env`:nx.MultiDiGraph
            Граф улично-дорожной сети
        `points`: dict
            Список стартовых узлов графа в которых размещены
            подразделения.
        `area`: pd.Series = None
            Маска узлов графа. Значениями True отмечены узлы графа - цели расчета леса Вороного.
            Если не указана, расчет производится для всех узлов графа.
        `k`: int = 1
            Количество подразделений которые следует добавить.
        '''

        # 0. Проверка корректности пришедших данных
        if not isinstance(env, nx.MultiDiGraph):
            raise TypeError("Тип аргумента `env` должен быть MultiDiGraph!")
        if not isinstance(points,dict):
            raise TypeError(f'Аргумент `points` должен иметь тип: dict'
                            f'Имеет: {type(points)}')
        if not area is None and not isinstance(area, pd.Series):
            raise TypeError(f'Аргумент `area` должен иметь тип `pd.Series`! Имеет {type(area)}')
        if k < 1:
            raise ValueError(f'Аргумент `k` должен быть >= 1! Имеет: {k}')

        # 1. Выбор случайных n узлов из числа не входящих в points
        points_set = set(points.keys())
        if area is None:
            nodes_set = set(env.nodes()) - points_set
        else:
            nodes_set = set(env.nodes()) & set(area[area].keys()) - points_set
        new_nodes = random.choices(list(nodes_set), k=k)

        return new_nodes


class GenesisNodeSelector(PointSelectorBase):
    '''
    Простой выбор случайного узла в графе
    '''
    def __init__(self,
                #  state_algorithm=MSF,
                 state_function: StateBase,
                 metric_function: MetricBase,
                 appr_val: float = 0.95,
                 weight='travel_time',
                 **kwargs) -> None:
        '''
        ## Аргументы
        `state_algorithm`: function
            Функция расчета кратчайших путей от единственного источника. 
            В качестве функции могут быть переданы реализации алгоритмов из пакета
            `networkx`. Например, реализация алгоритма Дейкстры: `nx.multi_source_dijkstra`.
            Пользователь может использовать собственные функции с
            интерфейсом `func(G: Graph, sources: Any, target: Any | None = None, cutoff: Any | None = None, 
            weight: str = "weight") -> (dict, dict)`
        `state_function`: StateBase
            функция расчета состояния окружения
        `appr_val`: = 0.95
            Доля узлов графа, покрытие которой считается приемлемой для принятия расчетной метрики. 
            Если при расчете метрик, из стартового узла (узлов) достижимо меньшее количество узлов,
            то такой узел не рассматривается.
        `weight`:str или function  = "travel_time"
            Имя поля содержащего вес ребер, или функция позволяющая вычислять 
            вес динамически.
        '''
        # self.state_algorithm = state_algorithm
        self.state_function = state_function
        self.metric_function = metric_function
        self.appr_val = appr_val
        self.weight = weight
        super().__init__(**kwargs)

    def __call__(self,
                env:nx.MultiDiGraph,
                points:dict,
                area: pd.Series = None,
                **kwargs):
        '''
        Запуск работы алгоритма

        ## Аргументы
        `env`:nx.MultiDiGraph
            Граф улично-дорожной сети
        `points`: dict
            Список стартовых узлов графа в которых размещены
            подразделения.
        `area`: pd.Series = None
            Маска узлов графа. Значениями True отмечены узлы графа - цели расчета леса Вороного.
            Если не указана, расчет производится для всех узлов графа.
        '''

        # 0. Проверка корректности пришедших данных
        if not isinstance(env, nx.MultiDiGraph):
            raise TypeError("Тип аргумента `env` должен быть MultiDiGraph!")
        if not isinstance(points,dict):
            raise TypeError(f'Аргумент `points` должен иметь тип: dict'
                            f'Имеет: {type(points)}')
        if not area is None and not isinstance(area, pd.Series):
            raise TypeError(f'Аргумент `area` должен иметь тип `pd.Series`! Имеет {type(area)}')

        # 1. Расчет состояния прибытия
        times, nearest = self.state_function(env = env,
                                             points = points,
                                             area = area,
                                             **kwargs)

        # 2. Группировка по деревьям Вороного
        # и вычисление наихудшего из них
        worst_unit_id = None
        worst_unit_metric = None
        for unit_id in nearest.unique():
            unit_area_nodes = nearest[nearest == unit_id].index.tolist()
            unit_times = times[unit_area_nodes]
            unit_metric = self.metric_function(unit_times)

            if worst_unit_id is None:
                worst_unit_id = unit_id
                worst_unit_metric = unit_metric
            else:
                if self.metric_function.compare(worst_unit_metric, unit_metric) == worst_unit_metric:
                    worst_unit_id = unit_id
                    worst_unit_metric = unit_metric

        # 3. Поиск наихудшего узла соседнего с наихудшим узлом
        worst_unit_node = get_dict_key(points, worst_unit_id)
        worst_node = None
        worst_node_metric = None
        for node in env[worst_unit_node]:
            times, nearest = self.state_function(env = env,
                                             points = [worst_unit_node, node],
                                             area = area,
                                             **kwargs)
            node_metric = self.metric_function(times)

            if worst_node is None:
                worst_node = node
                worst_node_metric = node_metric
            else:
                if self.metric_function.compare(worst_node_metric, node_metric) == node_metric:
                    worst_node = node
                    worst_node_metric = node_metric

        return worst_node