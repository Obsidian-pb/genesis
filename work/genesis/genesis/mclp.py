'''
Реализация алгоритмов поиска оптимального размещения нескольких наилучшим образом расположенных узлов (MCLP)
'''

import networkx as nx
import pandas as pd

from genesis.core import BestPointsBase, MetricBase, StateBase
from genesis.best_points import NodeMetric
from genesis.tools import list_dict_concat


class BestNodesKoptG(BestPointsBase):
    '''
    Поиск лучших узлов для размещения n объектов.

    Расчет производится алгоритмом k-mean адаптированным для расчета
    в графовом пространстве и абстрагированным от применения метрики
    mean (среднее).

    ## Область применения
    Определение размещения множества узлов в графе, при котором 
    обеспечиваются наилучшие некоторые целевые метрики. 
    Дает достаточно точное решение. Хорошо подходит для больших графов.
    '''

    def __init__(self,
                 state_function: StateBase,
                 metric_function: MetricBase,
                 best_point_function: BestPointsBase,
                 iterations:int=5,
                 appr_val_in_area=0,
                 **kwargs) -> None:
        '''
        ## Аргументы
        `state_function`: StateBase
            функция расчета состояния окружения
        `metric_function`: MetricBase
            Функция расчета метрики
        `best_point_function`: BestPointsBase
            Функция расчета лучшего размещения узла
        `iterations`:int=5
            Количество итераций расчета
        `appr_val_in_area`: int=0
            Доля узлов графа в пределах area, покрытие которой считается приемлемой для принятия расчетной метрики. 
            Если при расчете метрик, из стартового узла (узлов) достижимо меньшее количество узлов,
            то такой узел не рассматривается.
            При расчет размещения нескольких узлов неминуемо возникает ситуация при которой
            часть территории area будет недостижима. Поэтому по умолчанию считается
        '''
        
        self.best_point_function = best_point_function
        self.iterations = iterations
        self.appr_val_in_area = appr_val_in_area
        super().__init__(state_function, metric_function, **kwargs)


    def __call__(self,
                 env:nx.MultiDiGraph,
                 dynamic_nodes: list|dict,
                 static_nodes: list|dict = None,
                 before_iters_start_function: callable =None,
                 iter_calc_end_function: callable =None,
                 area: pd.Series = None,
                 **kwargs):
        '''
        ## Аргументы

        `env`:nx.MultiDiGraph
            Граф улично-дорожной сети
        `dynamic_nodes`: list|dict
            Список стартовых узлов графа в которых размещены
            подразделения оптимальные места которых следует определить.
        `static_nodes`: list|dict = None
            Список стартовых узлов графа в которых размещены
            подразделения изменять размещение которых не следует.
        `before_iters_start_function`: callable=None
            Функция выполняемая перед началом итеративного расчета.
            Сигнатура функции:
            ```
            before_iters_start_function(
                                    best_metric: float,
                                    dynamic_nodes: list|dict,
                                    static_nodes: list|dict
                                    )
            ```
            Если не указана, ничего не происходит.
        `iter_calc_end_function`: callable=None
            Функция выполняемая в конце каждой итерации.
            Сигнатура функции:
            ```
            before_iters_start_function(
                                    best_metric: float,
                                    dynamic_nodes: list|dict,
                                    static_nodes: list|dict
                                    )
            ```
            Если не указана, ничего не происходит.
        `area`: pd.Series = None
            Маска узлов графа. Значениями True отмечены узлы графа - цели расчета леса Вороного.
            Если не указана, расчет производится для всех узлов графа.

        ## Возвращает
        `best_dynamic_nodes, best_metric`: tuple[list | dict, float]
            Список или словарь лучших мест размещения, значение метрики metric_function
            для лучшего размещения.
        '''
        
        # 0. Проверка корректности пришедших данных
        if not isinstance(env, nx.MultiDiGraph):
            raise TypeError("Тип аргумента `env` должен быть MultiDiGraph!")
        if not static_nodes is None:
            if not ((isinstance(dynamic_nodes,list) and isinstance(static_nodes,list)) or \
                (isinstance(dynamic_nodes,dict) and isinstance(static_nodes,dict))):
                raise TypeError(f'Аргументы `dynamic_nodes` и `static_nodes` должны быть одинакового типа: list|dict'
                                f'Имеют: {type(dynamic_nodes)}, {type(static_nodes)}')
        if not area is None and not isinstance(area, pd.Series):
            raise TypeError(f'Аргумент `area` должен иметь тип `pd.Series`! Имеет {type(area)}')

        # Если передана область которую следует учитывать в расчете
        # установить для нее приемлемый охват равный `self.appr_val_in_area`
        # (0 по умолчанию)
        if not area is None:
            self.best_point_function.__setattr__('appr_val',
                                                 self.appr_val_in_area)

        # 1.1. Если статические узлы не указаны - заменяем значение переменной с None
        # на [] или {} в зависимости от типа данных `dynamic_nodes`
        if static_nodes is None:
            if isinstance(dynamic_nodes,list):
                static_nodes = []
            elif isinstance(dynamic_nodes,dict):
                static_nodes = {}

        # 1.2. Получение суммарного списка (или словаря) узлов для расчета состояния и метрик
        start_nodes = list_dict_concat(dynamic_nodes, static_nodes)

        # 2.1. Расчет состояния
        times, nearest = self.state_function(env=env, points=start_nodes, **kwargs)

        # 2.2. Расчет стартовой метрики состояния и определение стартового размещения
        best_metric = self.metric_function(times, area=area, **kwargs)
        best_dynamic_nodes = dynamic_nodes

        # 3. Выполняем функцию перед началом итераций
        if before_iters_start_function:
            before_iters_start_function(
                                    best_metric=best_metric,
                                    dynamic_nodes=dynamic_nodes,
                                    static_nodes=static_nodes
                                    )

        # 4. Итерации расчета лучшего размещения
        for iteration in range(self.iterations):

            # 1. Поиск для каждого из dinamic_nodes наилучшего размещения в пределах своей зоны обслуживания
            # 1.1. Для списка:
            if isinstance(dynamic_nodes, list):
                new_dynamic_nodes = []
                for dynamic_node in dynamic_nodes:

                    # Определяем список узлов в которые из узла dynamic_node можно прибыть первым
                    node_area_nodes = [n for n,v in nearest.items() if v==dynamic_node]

                    # Определяем подграф зоны обслуживания для узла dynamic_node
                    node_area_G = nx.subgraph(env, node_area_nodes)

                    # Определяем лучший узел
                    best_nodes, _ = self.best_point_function(env=node_area_G, 
                                                                    start_node=dynamic_node,
                                                                    area=area,
                                                                    **kwargs)[:2] # [:2] Это для ограничения вывода дебаг-данных в некоторых функциях
                    if isinstance(best_nodes, list):
                        best_nodes = best_nodes[0]
                    # Добавляем полученный узел в новый список
                    new_dynamic_nodes.append(best_nodes)
            # 1.2. Для словаря:
            else:
                new_dynamic_nodes = {}
                for dynamic_node_id, dynamic_node_key in dynamic_nodes.items():

                    # Определяем список узлов в которые из узла dynamic_node можно прибыть первым
                    node_area_nodes = [k for k,v in nearest.items() if v==dynamic_node_key]

                    # Определяем подграф зоны обслуживания для узла dynamic_node
                    node_area_G = nx.subgraph(env, node_area_nodes)

                    # Определяем лучший узел
                    best_nodes, _ = self.best_point_function(env=node_area_G, 
                                                                    start_node=dynamic_node_id,
                                                                    area=area,
                                                                    **kwargs)[:2] # [:2] Это для ограничения вывода дебаг-данных в некоторых функциях

                    if isinstance(best_nodes, list):
                        best_nodes = best_nodes[0]
                    # Добавляем полученный узел в новый список
                    new_dynamic_nodes[best_nodes] = dynamic_node_key

            # 2. Заменяем список dynamic_nodes списком с новыми, лучшими узлами
            dynamic_nodes = new_dynamic_nodes

            # 3. Приведение к типу переменной в соответствии с типом `dynamic_nodes`
            start_nodes = list_dict_concat(dynamic_nodes, static_nodes)

            # 4. Расчет состояния
            times, nearest = self.state_function(env=env, points=start_nodes, **kwargs)   # area=area, 

            # 5. Расчет метрики состояния
            state_metric = self.metric_function(times, area=area, **kwargs)

            # 6. Оценка метрики состояния
            if self.metric_function.compare(best_metric, state_metric) == state_metric:
                best_metric = state_metric
                best_dynamic_nodes = dynamic_nodes

            # 7. Выполняем функцию завершения расчета для итерации
            if iter_calc_end_function:
                iter_calc_end_function(i=iteration,
                                       best_metric=best_metric,
                                       dynamic_nodes=best_dynamic_nodes,
                                       static_nodes=static_nodes)

        return best_dynamic_nodes, best_metric

        
