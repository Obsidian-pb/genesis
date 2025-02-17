'''
Алгоритмы поиска оптимальных узлов графа.
'''

import random

import networkx as nx
import osmnx as ox
import numpy as np
import pandas as pd

from .core import BestPointsBase, MetricBase, StateBase
from .metrics import ArrivalTime
from .tools import get_all_neighbor_nodes



class NodeMetric(BestPointsBase):
    '''
    Расчет метрики для конкретного узла графа.
    
    ## Важно
    Применяется строго к графам!
    '''
    def __init__(self, state_function: StateBase,
                 metric_function: MetricBase,
                 appr_val = 0.95,
                 err_val=None,
                 **kwargs) -> None:
        '''
            `state_function`: StateBase
                функция расчета состояния окружения
            `metric_function`: MetricBase
                Функция расчета метрики
            `appr_val`: = 0.95
                Доля узлов графа, покрытие которой считается приемлемой для принятия расчетной метрики. 
                Если при расчете метрик, из стартового узла (узлов) достижимо меньшее количество узлов,
                то такой узел не рассматривается.
            `err_val`: any = None
                Значение которое будет возвращено в случае если из точки `node`
                невозможно будет достичь требуемой доли узлов графа.
        '''
        self.appr_val = appr_val
        self.err_val = err_val
        super().__init__(state_function, metric_function, **kwargs)

    def __call__(self, env:nx.MultiDiGraph, node:int, area=None, **kwargs):
        '''
            ## Параметры
            `env` : MultiDiGraph (G)
                Граф дорожной сети
            `node`: int
                Идентификатор узла графа для которого происходит расчет
            `area`: pd.Series = None
                Маска узлов графа. Значениями True отмечены узлы графа - цели расчета леса Вороного.
                Если не указана, расчет производится для всех узлов графа.
        '''

        # Если маска приемлемых узлов графа не передана,
        # то приемлемое количество узлов считается от количества узлов в графе
        # Иначе - от количества True в маске
        if area is None:
            appr_nodes_count = int(env.number_of_nodes() * self.appr_val)
        else:
            appr_nodes_count = int(sum(area) * self.appr_val)
        # # Приемлемое количество узлов считается от количества узлов в графе
        # appr_nodes_count = int(env.number_of_nodes() * self.appr_val)

        # Собственно расчет
        times, _ = self.state_function(env=env, points=[node], area=area, **kwargs)
        if len(times)>=appr_nodes_count:
            cur_val = self.metric_function(times, **kwargs)
        else:
            cur_val = self.err_val
        return cur_val


class BestNodesFull(BestPointsBase):
    '''
        Поиск лучших узлов графа полным перебором. 
        Могут быть возвращены только узлы из которых можно попасть в большую часть других узлов графа.
        Если таковых узлов нет, возвращается ошибка некорректности графа. 
        (граф должен быть проверен на корректность прежде чем будет передан функции)
        
        Узлы для которых метрика не может быть вычислена (например слабо связанные 
        с основным графом) не учитываются. 

        ## Область применения
        Определение размещения одного узла с наилучшими показателями. 
        Дает достаточно точное решение, однако плохо подходит для больших графов.
        Требует длительного времени на проведение расчетов.
        Вместе с тем позволяет определить поле пригодных узлов в тех случаях когда предполагается наличие 
        большого количества приемлемых мест размещения. Например, точек, размещение в которых пожарных депо позволяет обеспечить
        ИП-10 = 100%.

        ## Важно
        Следует помнить, что некорректные узлы в случае их учета посредством снижения appr_val могут 
        давать искаженное представление о метриках графа. При этом в реальности граф дорожной сети 
        как правило изобилует слабосвязанными узлами, поэтому учет только узлов обеспечивающих 100%
        достижимость всего графа может приводить к принципиальной невозможности расчета.
    '''
    def __init__(self,
                 state_function: StateBase,
                 metric_function: MetricBase,
                 appr_val: float = 0.95,
                 return_list: bool = False,
                 node_calc_end_function: callable = None,
                 **kwargs) -> None:
        '''
        `state_function` : StateBase
            Функция расчета состояния среды
        `metric_function` : MetricBase
            Функция оценки.
        `appr_val`: = 0.95
            Доля узлов графа, покрытие которой считается приемлемой для принятия расчетной метрики. 
            Если при расчете метрик, из стартового узла (узлов) достижимо меньшее количество узлов,
            то такой узел не рассматривается.
        `return_list`: = False
            Если True - вернет список всех лучших узлов. False - вернет только первый из списка.
            Свойство необходимо для соблюдения правил возврата данных `BestPointsBase`.
            Однако в ряде случаев может потребоваться получить список всех лучших узлов.
        `node_calc_end_function`:callable=None
            Функция вызываемая в конце расчета каждого узла.
            Сигнатура функции:
            ```
                node_calc_end_function()
            ```
        '''
        self.appr_val = appr_val
        self.node_calc_end_function = node_calc_end_function
        self.return_list = return_list
        super().__init__(state_function, metric_function, **kwargs)

    def __call__(self, env:   nx.MultiDiGraph,
                 area:        pd.Series = None,
                 start_point: int = None,
                 points_list:  set = None,
                 **kwargs):
        '''
        ## Параметры
        `env` : MultiDiGraph (G)
            Граф улично-дорожной сети
        `area`: pd.Series = None
            Маска узлов графа. Значениями True отмечены узлы графа - цели расчета леса Вороного.
            Если не указана, расчет производится для всех узлов графа.
        `points_list`: set = None
            Множество узлов графа которые будут рассмотрены в качестве кандидатов.
            Если не указан, то будут рассмотрены все узлы графа.
        

        ## Возвращает
        `best_nodes_list`, `best_metric`: tuple[list[Any | None], None]
            Множество - (идентификатор узла, значение метрики узла)
        '''

        if not isinstance(env, nx.MultiDiGraph):
            raise TypeError('Тип данных аргумента `env` должен быть nx.MultiDiGraph')
        if not area is None and not isinstance(area, pd.Series):
            raise TypeError(f'Аргумент `area` должен иметь тип `pd.Series`! Имеет {type(area)}')

        # Если списка узлов изначально не передано, рассматриваются все узлы графа
        nodes_list = points_list
        if nodes_list is None:
            nodes_list = env.nodes()

        # # Если маска приемлемых узлов графа не передана,
        # # то приемлемое количество узлов считается от количества узлов в графе
        # # Иначе - от количества True в маске
        # if area is None:
        #     appr_nodes_count = int(env.number_of_nodes() * self.appr_val)
        # else:
        #     appr_nodes_count = int(sum(area) * self.appr_val)

        best_metric = None
        # best_node = None
        best_nodes_list = []
        # best_nodes_list = set()

        for node in nodes_list:

            # # расчет среды
            # times, _ = self.state_function(env=env, points=[node], area=area, **kwargs)

            # # проверка на корректность охвата графа
            # if len(times)>=appr_nodes_count:

            #     # расчет метрики среды для текущего узла `node`
            #     node_metric = self.metric_function(times, **kwargs)
            
            node_metric_func = NodeMetric(self.state_function, self.metric_function, self.appr_val, err_val=None)
            node_metric = node_metric_func(env=env, node=node, area=area)

            # проверка на корректность охвата графа
            if node_metric:

                # если лучшая метрика еще не указана, присваиваем текущее значение
                if best_metric is None:
                    best_metric = node_metric
                    best_nodes_list = [node]
                    # best_nodes_list = set([node])
                    # best_node = node
                # проверяем лучше ли метрика среды для текущего узла, чем лучшая до этого
                else:
                    # if best_metric > node_metric:
                    if self.metric_function.compare(best_metric, node_metric) == node_metric:
                        if best_metric == node_metric:
                            best_nodes_list.append(node)
                            # best_nodes_list.add(node)
                        else:
                            best_nodes_list = [node]
                            # best_nodes_list = set([node])
                        # best_node = node
                        best_metric = node_metric

            # выполняем функцию завершения расчета для узла
            if self.node_calc_end_function:
                self.node_calc_end_function()

        if self.return_list:
            return best_nodes_list, best_metric
        return best_nodes_list[0], best_metric



class BestNodeHillClimbing(BestPointsBase):
    '''
        Поиск лучшего узла графа с использованием алгоритма скалолаза (hill climbing). 
        Могут быть возвращены только узлы из которых можно попасть в большую часть других узлов графа.
        Если таковых узлов нет, возвращается ошибка некорректности графа. 
        (граф должен быть проверен на корректность прежде чем будет передан функции)
        
        Узлы для которых метрика не может быть вычислена (например слабо связанные 
        с основным графом) не учитываются. 

        ## Область применения
        Определение размещения одного узла с наилучшими показателями. 
        Дает достаточно точное решение. Хорошо подходит для больших графов.
        Может давать оценку только для полного набора узлов графа (в отличие от BNF).
    '''
    def __init__(self,
                 state_function: StateBase,
                 metric_function: MetricBase,
                 appr_val: float = 0.95,
                 all_neighbors: bool=True,
                 node_calc_end_function:callable=None,
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
        `all_neighbors`: bool=True
            Если True рассматриваются все узлы смежные с рассчитываемым узлом.
            Если False - только исходящие.
        `node_calc_end_function`: callable=None
            Функция выполняемая в конце расчета каждого узла.
        '''
        if appr_val > 1 or appr_val<0:
            raise ValueError(f'Аргумент `appr_val` должен находиться в диапазоне (0, 1)!'
                             f'Сейчас {appr_val}')
        self.appr_val = appr_val
        self.all_neighbors=all_neighbors
        self.node_calc_end_function = node_calc_end_function
        super().__init__(state_function, metric_function, **kwargs)

    def __call__(self,
                 env:         nx.MultiDiGraph,
                 area:        pd.Series=None,
                 start_point: int = None,
                 points_list: set = None,
                 debug_route: bool=False,
                #  node_calc_end_function:callable=None,
                 **kwargs):
        '''
        `env`:nx.MultiDiGraph
            Граф улично-дорожной сети
        `area`: pd.Series = None
            Маска узлов графа. Значениями True отмечены узлы графа - цели расчета леса Вороного.
            Если не указана, расчет производится для всех узлов графа.
        `start_point`: int
            Идентификатор стартового узла
        `points_list`: set = None
            !Для данного алгоритма не используется! Множество точек среды которые будут рассмотрены в качестве кандидатов.
            Если не указан, то будут рассмотрены все узлы графа.
        `debug_route`: bool=False
            Если True - возвращается также маршрут по которому проходил алгоритм
            в процессе поиска
        '''
        
        if not isinstance(env, nx.MultiDiGraph):
            raise TypeError("Тип переменной `env` должен быть MultiDiGraph!")
        

        node_metric_func = NodeMetric(self.state_function, self.metric_function, self.appr_val, err_val=None, **kwargs)

        nodes_metric = {}
        route={}

        # Если маска приемлемых узлов графа не передана,
        # то приемлемое количество узлов считается от количества узлов в графе
        # Иначе - от количества True в маске
        # if area is None:
        #     appr_nodes_count = int(env.number_of_nodes() * self.appr_val)
        # else:
        #     appr_nodes_count = int(sum(area) * self.appr_val)

        start_node = start_point
        if start_node is None:
            # Поиск первого узла из которого можно попасть во все остальные узлы ГДС !ВАЖНО!
            # Иначе можно оказаться в тупике из которого нет выхода
            node_metric = None
            i=0
            nodes_list = list(env.nodes())
            while node_metric is None:
                if i>=env.number_of_nodes():
                    raise ValueError('Определить наиболее выгодный стартовый узел невозможно, ' \
                    'в связи с неприемлемой несвязностью графа')
                start_node = nodes_list[i]

                # Расчет метрики для узла `start_node`
                node_metric = node_metric_func(env=env, node=start_node, area=area, **kwargs)
                # Если указана расчетная область и метрика не была рассчитана
                if (node_metric is None) and (not area is None):
                    node_metric = node_metric_func(env=env, node=start_node, **kwargs)

                nodes_metric[start_node] = node_metric
                i+=1
        else:
            # Использование переданного стартового узла
            if not isinstance(start_node,int):
                raise TypeError('Тип данных start_node должен быть только int!')

            node_metric = node_metric_func(env=env, node=start_node, area=area, **kwargs)

            if node_metric is None:
                if not area is None:
                    # raise ValueError(f'Достичь области `area` из стартового узла {start_node}' \
                    #                  'невозможно,')
                    # ВАЖНО! будет произведена оценка оценка метрики для подграфа зоны обслуживания подразделения
                    node_metric = node_metric_func(env=env, node=start_node, **kwargs)
                else:
                    raise ValueError('Указанный стартовый узел неприемлем, в связи с его слабой ' \
                        'связностью с остальной частью графа')
            
            nodes_metric[start_node] = node_metric

        route[start_node] = node_metric
        # logging.debug('ПЕРВЫЙ УЗЕЛ {}, метрика {}'.format(start_node, node_metric))

        # Пошаговый поиск лучшего узла от start_node
        best_metric = node_metric
        best_node = start_node
        tmp_node=None
        while best_node!=tmp_node:
            tmp_node = best_node

            if self.all_neighbors:
                nnodes = get_all_neighbor_nodes(env, tmp_node)
            else:
                nnodes = env[tmp_node]

            for node in nnodes:
                if node in nodes_metric:
                    node_metric = nodes_metric[node]
                else:
                    node_metric = node_metric_func(env=env, node=node, area=area, **kwargs)
                    nodes_metric[node] = node_metric

                # logging.debug('УЗЕЛ {}, метрика {}'.format(node, node_metric))

                # Если метрики одинаковы, в данном случае - ситуация неприемлемая и должна быть исключена.
                if best_metric!=node_metric and \
                        self.metric_function.compare(best_metric, node_metric) == node_metric:
                    best_node = node
                    best_metric = node_metric

            route[best_node] = best_metric
            # logging.debug('ЛУЧШИЙ УЗЕЛ {}, метрика {}'.format(best_node, best_metric))

            # выполняем функцию завершения расчета для узла
            if self.node_calc_end_function:
                self.node_calc_end_function(best_node=best_node, best_metric=best_metric)

        if debug_route:
            return best_node, best_metric, route
        return best_node, best_metric


# Временно здесь - потом вынести в отдельный модель для кастомизированных решений
class BestNodeHillClimbing_maxMean(BestNodeHillClimbing):
    def __init__(self, 
                 state_function: StateBase,
                 metric_function: MetricBase = None,
                 appr_val: float = 0.95,
                 all_neighbors: bool = True,
                 **kwargs) -> None:
        super().__init__(state_function, metric_function, appr_val, all_neighbors, **kwargs)

    def __call__(self, env:   nx.MultiDiGraph,
                 area:        pd.Series = None,
                 start_point: int = None,
                 points_list: set = None,
                 debug_route: bool = False,
                 node_calc_end_function: callable = None,
                 **kwargs):

        bnch_max = BestNodeHillClimbing(state_function=self.state_function,
                                        metric_function=ArrivalTime(np.max), appr_val=self.appr_val, all_nodes=self.all_neighbors)
        bnch_mean = BestNodeHillClimbing(state_function=self.state_function,
                                         metric_function=ArrivalTime(), appr_val=self.appr_val, all_nodes=self.all_neighbors)

        best_node, best_metric = bnch_max(env=env, area=area, start_point=start_point, points_list=points_list)
        best_node, best_metric = bnch_mean(env=env, area=area, start_point=start_point, points_list=points_list)

        # выполняем функцию завершения расчета для узла
        if node_calc_end_function:
            node_calc_end_function()

        return best_node, best_metric

class BestNodesHalfDiameter(BestPointsBase):
    '''
        Поиск лучших узлов графа с использованием алгоритма расчета точки в середине графа. 
        Могут быть возвращены только узлы из которых можно попасть в большую часть других узлов графа.
        Если таковых узлов нет, возвращается ошибка некорректности графа. 
        (граф должен быть проверен на корректность прежде чем будет передан функции)
        
        Узлы для которых метрика не может быть вычислена (например слабо связанные 
        с основным графом) не учитываются. 

        ## Область применения
        Определение размещения одного узла с наилучшими показателями. 
        Дает приближенное решение. Не рекомендуется к использованию как 
        самостоятельное решение. Однако может использоваться как способ
        ускорения работы других функций позволяющих искать размещение от
        стартового узла (BestNodeHillClimbing, BestNodeHillClimbing_maxMean и т.д.)
    '''
    def __init__(self,
                 state_function: StateBase = None,
                 metric_function: MetricBase = None,
                 weight: str = 'travel_time',
                 **kwargs) -> None:
        '''
        ## Аргументы
        `state_function`: StateBase
            Не используется! функция расчета состояния окружения
        `metric_function`: MetricBase
            Не используется! Функция расчета метрики
        `weight`:str или callable  = "travel_time"
            Имя поля содержащего вес ребер, или функция позволяющая вычислять 
            вес динамически.
        '''
        self.weight = weight
        super().__init__(state_function, metric_function, **kwargs)

    def __call__(self, env:nx.MultiDiGraph, area=None, **kwargs):
        '''
        ## Аргументы

        `env`:nx.MultiDiGraph
            Граф улично-дорожной сети
        `area`
            Не используется!
        '''
        # Проверка корректности пришедших данных
        if not isinstance(env, nx.MultiDiGraph):
            raise TypeError(f'Неверный тип аргумента `env`! Должен быть `nx.MultiDiGraph` - имеется `{type(env)}`.')

        # 1 Выбираем произвольную точку. По-умолчанию берем просто первую из списка узлов
        nd = list(env.nodes())[0]

        # 2.1 Находим самую отдаленную от нее (входящую) -- периферия №1
        lngs = nx.shortest_path_length(env, target=nd, weight=self.weight)
        corner_1 = max(lngs, key=lngs.get)

        # 2.2 Находим самую отдаленную от нее (входящую) -- периферия №2
        lngs = nx.shortest_path_length(env, target=corner_1, weight=self.weight)
        corner_2 = max(lngs, key=lngs.get)

        # # 2.3 Находим самую отдаленную от нее (входящую) -- периферия №3 (уточняющая)
        # lngs = nx.shortest_path_length(env, target=corner_2, weight=self.weight)
        # corner_3 = max(lngs, key=lngs.get)

        # Рассчитываем длину диаметра и маршрут следования по нему
        diameter = nx.shortest_path_length(env, corner_2, corner_1, weight=self.weight)
        short_path = nx.shortest_path(env, corner_2, corner_1, weight=self.weight)
        # diameter = nx.shortest_path_length(env, corner_1, corner_2, weight=self.weight)
        # short_path = nx.shortest_path(env, corner_1, corner_2, weight=self.weight)

        # Если в кратчайшем маршруте менее двух точек, возвращаем первую
        if len(short_path) < 2:
            return short_path[0], None

        # Находим точку примерно по середине диаметра
        tot_len = 0
        nd1 = short_path[0]
        for nd1, nd2 in zip(short_path[:-1],short_path[1:]):
            cur_len = env.get_edge_data(nd1, nd2, 0)[self.weight]
            tot_len += cur_len
            if tot_len >= diameter / 2: break

        return nd1, None


class BestNodeMonkey(BestNodeHillClimbing):
    '''
        Поиск лучших узлов графа с использованием алгоритма обезьяньего поиска
        (Monkey Search Algorithm).
        Могут быть возвращены только узлы из которых можно попасть в большую часть 
        других узлов графа.
        Если таковых узлов нет, возвращается ошибка некорректности графа.
        (граф должен быть проверен на корректность прежде чем будет передан функции)

        Узлы для которых метрика не может быть вычислена (например слабо связанные
        с основным графом) не учитываются.

        ## Область применения
        Определение размещения одного узла с наилучшими показателями.
        Дает достаточно точное решение. Хорошо подходит для больших графов.
    '''
    def __init__(self,
                 state_function: StateBase,
                 metric_function: MetricBase,
                 appr_val: float = 0.95,
                 all_neighbors: bool=True,
                 global_jumps_count: int = 3,
                 local_jumps_count: int = 10,
                 local_jump_max_distance: int = 1000,
                 after_global_jump_function: callable = None,
                 after_local_jump_function: callable = None,
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
        `all_neighbors`: bool=True
            Если True рассматриваются все узлы смежные с рассчитываемым узлом.
            Если False - только исходящие.
        `global_jumps_count`: int=3
            Количество глобальных прыжков (начиная со стартового).
            Глобальный прыжок осуществляется путем случайного выбора произвольного узла графа.
        `local_jumps_count`: int=10
            Количество локальных прыжков.
        `local_jump_max_distance`: int=1000
            Максимальное расстояние локального прыжка.
            Локальный прыжок осуществляется путем случайного выбора 
            узла графа на расстоянии `local_jump_max_distance` метров от текущей вершины.
        `after_global_jump_function`: callable=None
            Функция вызываемая после каждого глобального прыжка.
        `after_local_jump_function`: callable=None
            Функция вызывается после каждого локального прыжка
        '''
        self.node_metric_func = NodeMetric(state_function,
                                           metric_function,
                                           appr_val,
                                           err_val=None,
                                           **kwargs)
        self.global_jumps_count = global_jumps_count
        self.local_jumps_count = local_jumps_count
        self.local_jump_max_distance = local_jump_max_distance
        self.after_global_jump_function = after_global_jump_function
        self.after_local_jump_function = after_local_jump_function
        super().__init__(state_function,
                         metric_function,
                         appr_val=appr_val,
                         all_neighbors=all_neighbors,
                         **kwargs)


    def _get_sample_node(self, env, area, points_list, **kwargs):
        '''
        Получение случайного узла.
        Из узла можно попасть в большую часть других узлов графа (согласно `appr_val`)
        '''
        node_metric = None
        i=0
        if points_list is None:
            nodes_list = list(env.nodes())
        else:
            nodes_list = points_list
        while node_metric is None:
            if i>=env.number_of_nodes():
                raise ValueError('Определить наиболее выгодный стартовый узел невозможно, ' \
                'в связи с неприемлемой несвязностью графа')
            start_node = random.choice(nodes_list)

            # Расчет метрики для узла `start_node`
            node_metric = self.node_metric_func(env=env, node=start_node, area=area, **kwargs)
            # Если указана расчетная область и метрика не была рассчитана
            if (node_metric is None) and (not area is None):
                node_metric = self.node_metric_func(env=env, node=start_node, **kwargs)

            i+=1

        return start_node, node_metric


    def __call__(self,
                 env: nx.MultiDiGraph,
                 area = None,
                 start_point: int = None,
                 points_list:  set = None,
                 **kwargs) -> tuple[int | None, float | None]:
        '''
        Реализация: при помощи BestNodesHillClimbing ищется лучшая точка, 
        после чего обезьяна прыгает по ближайшим вершинам и вновь использует BestNodesHillClimbing.

        Так, пока не будет найден глобальный оптимум или не будет достигнуто количество итераций.

        ## Аргументы
        `env`:nx.MultiDiGraph
            Граф улично-дорожной сети
        `area`: pd.Series = None
            Маска узлов графа. Значениями True отмечены узлы графа - цели расчета леса Вороного.
            Если не указана, расчет производится для всех узлов графа.
        `start_point`: int
            !Для данного алгоритма не используется! Идентификатор стартового узла
        `points_list`: set = None
            !Для данного алгоритма не используется! Множество точек среды которые будут рассмотрены в качестве кандидатов.
            Если не указан, то будут рассмотрены все узлы графа.

        ## Возвращает
        `best_node`: int, `best_metric`: float
            Лучший узел, лучшая метрика
        '''

        if not isinstance(env, nx.MultiDiGraph):
            raise TypeError("Тип переменной `env` должен быть MultiDiGraph!")
        

        # Первый глобальный прыжок - случайный выбор старта
        # ! Здесь потом заменить `_get_sample_node`` на передаваемую функцию
        start_node = start_point
        if start_node is None:
            start_node, node_metric = self._get_sample_node(env, area, points_list, **kwargs)
        else:
            # Расчет метрики для узла `start_node`
            node_metric = self.node_metric_func(env=env, node=start_node, area=area, **kwargs)
            # Если указана расчетная область и метрика не была рассчитана
            if (node_metric is None) and (not area is None):
                node_metric = self.node_metric_func(env=env, node=start_node, **kwargs)

        best_node = start_node
        best_metric  = node_metric


        # Совершаем прыжки, начиная с первого
        for global_jump_number in range(self.global_jumps_count):

            # 1 Подъем на гору
            try:
                best_node_local, best_metric_local = super().__call__(
                    env=env,
                    area=area,
                    start_point=start_node,
                    # points_list=points_list,
                    **kwargs,
                    )
            except Exception as _:
                best_node_local, best_metric_local = None, None

            # Проверка на улучшение метрики и узла
            if best_node != best_node_local and \
                    self.metric_function.compare(best_metric, best_metric_local) == best_metric_local:
                best_node = best_node_local
                best_metric = best_metric_local

            # Событие после подъема на гору
            if self.after_global_jump_function is not None:
                self.after_global_jump_function(
                    global_jump_number = global_jump_number,
                    best_node = best_node,
                    best_metric = best_metric,
                    best_node_current = best_node_local,
                    best_metric_current = best_metric_local
                    )

            # 2 Локальные прыжки
            # 2.1 Определение узлов в округе
            g_nodes = ox.graph_to_gdfs(env, edges=False)
            if not ox.projection.is_projected(g_nodes.crs):
                g_nodes = ox.projection.project_gdf(g_nodes)
            buffer = g_nodes.loc[best_node_local:best_node_local].geometry.buffer(self.local_jump_max_distance)
            nodes_in_buffer = g_nodes[g_nodes.within(buffer.iloc[0])]
            nodes_in_buffer = list(nodes_in_buffer.index)

            # 2.2 Локальные прыжки
            global_number = 0
            jump_number = 0
            # while jump_number <= self.local_jumps_count:
            while jump_number < self.local_jumps_count:
                # global_number+=1
                # jump_number+=1
                jump_node = random.choice(nodes_in_buffer)
                # Вычисление метрики для узла `jump_node`
                try:
                    best_node_after_jump, best_metric_after_jump = super().__call__(env=env,
                                                               area=area,
                                                               start_point=jump_node,
                                                            #    points_list=points_list,
                                                               **kwargs)
                except Exception as _:
                    best_node_after_jump, best_metric_after_jump = None, None

                # if best_metric_after_jump<best_metric:  # Здесь заменить на Compare
                if best_node != best_node_after_jump and \
                        self.metric_function.compare(best_metric, best_metric_after_jump) == best_metric_after_jump:
                    best_node = best_node_after_jump
                    best_metric = best_metric_after_jump
                    jump_number = -1
                    # Переход к новой вершине
                    buffer = g_nodes.loc[best_node_after_jump:best_node_after_jump].geometry.buffer(self.local_jump_max_distance)
                    nodes_in_buffer = g_nodes[g_nodes.within(buffer.iloc[0])]
                    nodes_in_buffer = list(nodes_in_buffer.index)

                # Событие после подъема на гору
                if self.after_local_jump_function is not None:
                    self.after_local_jump_function(
                        global_jump_number = global_jump_number,
                        local_jump_number = jump_number,
                        best_node = best_node,
                        best_metric = best_metric,
                        best_node_current = best_node_after_jump,
                        best_metric_current = best_metric_after_jump
                        )
                global_number+=1
                jump_number+=1

            # Глобальный прыжок (выбор нового случайного узла)
            start_node, node_metric = self._get_sample_node(env, area, points_list, **kwargs)

        return best_node, best_metric


class BestNodeBee(BestNodeHillClimbing):
    '''
        Поиск лучших узлов графа с использованием алгоритма пчелиной колонии
        (Artificial Bee Colony Optimization, ABC).
        Могут быть возвращены только узлы из которых можно попасть в большую часть 
        других узлов графа.
        Если таковых узлов нет, возвращается ошибка некорректности графа.
        (граф должен быть проверен на корректность прежде чем будет передан функции)

        Узлы для которых метрика не может быть вычислена (например слабо связанные
        с основным графом) не учитываются.

        ## Область применения
        Определение размещения одного узла с наилучшими показателями.
        Дает достаточно точное решение. Хорошо подходит для больших графов.
    '''
    def __init__(self,
                 state_function: StateBase,
                 metric_function: MetricBase,
                 appr_val: float = 0.95,
                 all_neighbors: bool=True,
                 scouts_count: int = 100,
                 best_scouts_count: int = 5,
                #  after_local_jump_function: callable = None,
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
        `all_neighbors`: bool=True
            Если True рассматриваются все узлы смежные с рассчитываемым узлом.
            Если False - только исходящие.
        `scouts_count`: int=100
            Количество пчел-разведчиков.
        `best_scouts_count`: int=5
            Количество лучших пчел-разведчиков.
            Для них производится дальнейшая оптимизация.
        
        '''
        self.node_metric_func = NodeMetric(state_function,
                                           metric_function,
                                           appr_val,
                                           err_val=None,
                                           **kwargs)
        self.scouts_count = scouts_count
        self.best_scouts_count = best_scouts_count
        super().__init__(state_function,
                         metric_function,
                         appr_val=appr_val,
                         all_neighbors=all_neighbors,
                         **kwargs)


    def __call__(self,
                 env:nx.MultiDiGraph,
                 area=None,
                 start_point: int = None,
                 points_list: set = None,
                 **kwargs) -> tuple[int | None, float | None]:
        '''
        Реализация: `scouts_count` пчел-разведчиков случайным образом проверяют узлы
        
        при помощи BestNodesHillClimbing ищется лучшая точка, 
        после чего обезьяна прыгает по ближайшим вершинам и вновь использует BestNodesHillClimbing.

        Так, пока не будет найден глобальный оптимум или не будет достигнуто количество итераций.

        ## Аргументы
        `env`:nx.MultiDiGraph
            Граф улично-дорожной сети
        `area`: pd.Series = None
            Маска узлов графа. Значениями True отмечены узлы графа - цели расчета леса Вороного.
            Если не указана, расчет производится для всех узлов графа.
        `start_point`: int
            Идентификатор стартовой точки
        `points_list`:set=None
            Множество узлов графа которые будут рассмотрены в качестве кандидатов.
            Если не указан, то будут рассмотрены все узлы графа.

        ## Возвращает
        `best_node`: int, `best_metric`: float
            Лучший узел, лучшая метрика
        '''

        if not isinstance(env, nx.MultiDiGraph):
            raise TypeError("Тип переменной `env` должен быть MultiDiGraph!")
        if not area is None and not isinstance(area, pd.Series):
            raise TypeError(f'Аргумент `area` должен иметь тип `pd.Series`! Имеет {type(area)}')

        # Если списка узлов изначально не передано, рассматриваются все узлы графа
        # Здесь возможначпроблема, т.к. при дальнейшем поиске в любом случае оптимальными могут быть признаны узлы не из списка
        nodes_list = points_list
        if nodes_list is None:
            nodes_list = env.nodes()

        # 1. Разведка местности
        t_list = []
        t_metric = []
        for start_node in random.choices(list(nodes_list), k=self.scouts_count):
            start_metric = self.node_metric_func(env=env, area=area, node=start_node)
            t_list.append(start_node)
            t_metric.append(start_metric)
        
        # 2. Выбираем результаты лучших пчел-разведчиков
        tdf = pd.DataFrame({'node':t_list, 'metric':t_metric})
        if self.metric_function.compare(1,2)==2:
            tdf = tdf.sort_values('metric', ascending=False)
        else:
            tdf = tdf.sort_values('metric', ascending=True)
        # tdf.sort_values('metric', ascending=self.metric_function.compare(1,2)==1)
        # print(tdf['metric'][:10])

        # 3. Для каждого из лучших результатов пытаемся найти еще лучшие значения метрики в окрестности
        best_node = None
        best_metric  = None
        for node in tdf['node'][:self.best_scouts_count]:
            cur_node, cur_metric = super().__call__(
                    env=env,
                    area=area,
                    start_point=node,
                    # **kwargs,
                    )

            if best_node is None:
                best_node, best_metric = cur_node, cur_metric
            else:
                if best_node != cur_node and \
                        self.metric_function.compare(best_metric, cur_metric) == cur_metric:
                    best_node, best_metric = cur_node, cur_metric

        return best_node, best_metric