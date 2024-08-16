'''
Алгоритмы выбора узлов.
'''


import random
import warnings

import pandas as pd
import networkx as nx

from genesis.core import MetricBase, PointSelectorBase, StateBase
from genesis.tools import get_dict_key



class RandomNodesSelector(PointSelectorBase):
    '''
    Простой выбор случайного узла в графе
    '''
    def __init__(self, nodes_list:set=None, **kwargs) -> None:
        '''
        Простой выбор случайного узла в графе

        `nodes_list`:set=None
            Множество узлов графа которые будут рассмотрены в качестве кандидатов.
            Если не указан, то будут рассмотрены все узлы графа.
        '''
        self.nodes_list = nodes_list
        super().__init__(**kwargs)

    def __call__(self,
                env:nx.MultiDiGraph,
                points:dict,
                area: pd.Series = None,
                # nodes_list:set=None,
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
        if len(points) < 1:
            raise ValueError('Аргумент `points` должен содержать хотя бы 1 элемент! ' + \
                             'В случае если в `env` отсутствуют известные размещения `points`, ' + \
                             'используйте методы класса `BestPointsBase`')
        if not area is None and not isinstance(area, pd.Series):
            raise TypeError(f'Аргумент `area` должен иметь тип `pd.Series`! Имеет {type(area)}')
        if k < 1:
            raise ValueError(f'Аргумент `k` должен быть >= 1! Имеет: {k}')
        
        if k != 1:
            warnings.warn(f'Аргумент `k` не желательно делать отличным от 1! Имеет: {k}. Использовать с осторожностью!')

        # 1. Выбор случайных n узлов из числа не входящих в points
        points_set = set(points.keys())
        # if area is None:
        #     nodes_set = set(env.nodes()) - points_set
        # else:
        #     nodes_set = set(env.nodes()) & set(area[area].keys()) - points_set
        if self.nodes_list is None:
            nodes_set = set(env.nodes()) - points_set
        else:
            nodes_set = set(env.nodes()) & self.nodes_list - points_set            
        new_nodes = random.choices(list(nodes_set), k=k)

        # Если нужно получить один узел, возвращаем вместо списка значение int
        if len(new_nodes)==1:
            return new_nodes[0]
        return new_nodes


class GenesisNodeSelector(PointSelectorBase):
    '''
    Выбор наихудшего узла соседнего с наихудшим подразделением
    '''
    def __init__(self,
                 state_function: StateBase,
                 metric_function: MetricBase,
                 appr_val: float = 0.95,
                 weight='travel_time',
                 **kwargs) -> None:
        '''
        ## Аргументы
        `state_function`: StateBase
            функция расчета состояния окружения
        `metric_function`: MetricBase
            Функция расчета метрики
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
        if len(points) < 1:
            raise ValueError('Аргумент `points` должен содержать хотя бы 1 элемент! ' + \
                             'В случае если в `env` отсутствуют известные размещения `points`, ' + \
                             'используйте методы класса `BestPointsBase`')
        if not area is None and not isinstance(area, pd.Series):
            raise TypeError(f'Аргумент `area` должен иметь тип `pd.Series`! Имеет {type(area)}')

        # 1. В случае, если указана area определяем подразделения лежащие внутри area
        if area is None:
            points_scope = points   #.copy()
        else:
            points_scope = dict(filter(lambda x: x[0] in area[area].index, points.items()))   #.copy()
            if len(points_scope) != len(points):
                diff = {k:v for k,v in points.items() if not k in points_scope.keys()}
                warnings.warn(f'{diff} лежат вне пределов `area`. Результат определения следующей точки может быть не верен')


        # 1. Расчет состояния прибытия
        times, nearest = self.state_function(env = env,
                                             points = points_scope,
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

        # 3. Поиск наихудшего узла соседнего с наихудшим подразделением
        worst_unit_node = get_dict_key(points_scope, worst_unit_id)
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


class FarNodeSelector(PointSelectorBase):
    '''
    Выбор наиболее удаленного от имеющихся размещений узла, 
    (?) из которого при этом можно попасть
    в большую часть графа.

    `nodes_list`:set=None
            Множество узлов графа которые будут рассмотрены в качестве кандидатов.
            Если не указан, то будут рассмотрены все узлы графа.
    '''
    def __init__(self,
                 state_function: StateBase,
                #  metric_function: MetricBase,
                 nodes_list:set=None,
                 appr_val: float = 0.5,
                 weight='travel_time',
                 **kwargs) -> None:
        '''
        ## Аргументы
        `state_function`: StateBase
            функция расчета состояния окружения
        `metric_function`: MetricBase
            Функция расчета метрики
        `appr_val`: = 0.5
            Доля узлов графа, покрытие которой считается приемлемой для принятия расчетной метрики. 
            Если при расчете метрик, из стартового узла (узлов) достижимо меньшее количество узлов,
            то такой узел не рассматривается.
        `weight`:str или callable  = "travel_time"
            Имя поля содержащего вес ребер, или функция позволяющая вычислять 
            вес динамически.
        `nodes_list`:set=None
            Множество узлов графа которые будут рассмотрены в качестве кандидатов.
            Если не указан, то будут рассмотрены все узлы графа.
        '''
        self.state_function = state_function
        # self.metric_function = metric_function
        self.appr_val = appr_val
        self.weight = weight
        self.nodes_list = nodes_list
        super().__init__(**kwargs)

    def __call__(self,
                env:nx.MultiDiGraph,
                points:dict,
                area: pd.Series = None,
                # nodes_list:set=None,
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
        times, _ = self.state_function(env = env,
                                             points = points,
                                             area = area,
                                             **kwargs)

        # 2. Сортировка узлов по времени прибытия
        times = times.sort_values(ascending=False)


        # 3. Последовательный перебор наихудших узлов и оценка достижимости из каждого из них
        # 3.1. Определение количества допустимых узлов
        # ... Тут нужно подумать ...
        if area is None:
            appr_nodes_count = int(env.number_of_nodes()*self.appr_val)
        else:
            appr_nodes_count = int(area.sum()*self.appr_val)
        # 3.2. Если передан список возможных узлов, то ограничиваемся им
        # Иначе используем все times
        if not self.nodes_list is None:
            times = times[times.index.isin(self.nodes_list)]
        # 3.3. Перебор узлов
        for node in times.index:
            node_times, _ = self.state_function(env = env,
                                                points = [node],
                                                area = area,
                                                **kwargs)
            # print(node, len(node_times), appr_nodes_count)
            if len(node_times) >= appr_nodes_count:
                return node

        # 4. Если по какой-то причине ни один узел не был найден вызываем ошибку
        raise LookupError('Не удалось найти ни одного узла')
