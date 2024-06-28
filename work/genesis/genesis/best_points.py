'''
Алгоритмы поиска оптимальных узлов графа.
'''

# import numpy as np
import networkx as nx
import pandas as pd
from genesis.core import BestPointsBase, MetricBase, StateBase
from genesis.tools import get_all_neighbor_nodes



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
                 **kwargs) -> None:
        '''
        `state_function` : StateBase
            Функция расчета состояния среды
        `metric_function` : MetricBase
            Функция оценки. Если не указана, используется оценка по минимальному расстоянию.
        `appr_val`: = 0.95
            Доля узлов графа, покрытие которой считается приемлемой для принятия расчетной метрики. 
            Если при расчете метрик, из стартового узла (узлов) достижимо меньшее количество узлов,
            то такой узел не рассматривается.
        '''
        self.appr_val = appr_val
        super().__init__(state_function, metric_function, **kwargs)

    def __call__(self, env:nx.MultiDiGraph,
                 area:pd.Series=None,
                 nodes_list:set=None,
                 node_calc_end_function:callable=None,
                 **kwargs):
        '''
        ## Параметры
        `env` : MultiDiGraph (G)
            Граф улично-дорожной сети
        `area`: pd.Series = None
            Маска узлов графа. Значениями True отмечены узлы графа - цели расчета леса Вороного.
            Если не указана, расчет производится для всех узлов графа.
        `nodes_list`:set=None
            Множество узлов графа которые будут рассмотрены в качестве кандидатов.
            Если не указан, то будут рассмотрены все узлы графа.
        `node_calc_end_function`:callable=None
            Функция вызываемая в конце расчета каждого узла.
            Сигнатура функции:
            ```
                node_calc_end_function()
            ```

        ## Возвращает
        `best_nodes_list`, `best_metric`: tuple[list[Any | None], None]
            Множество - (идентификатор узла, значение метрики узла)
        '''

        if not isinstance(env, nx.MultiDiGraph):
            raise TypeError('Тип данных аргумента `env` должен быть nx.MultiDiGraph')
        if not area is None and not isinstance(area, pd.Series):
            raise TypeError(f'Аргумент `area` должен иметь тип `pd.Series`! Имеет {type(area)}')

        # Если списка узлов изначально не передано, рассматриваются все узлы графа
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
            if node_calc_end_function:
                node_calc_end_function()

        return list(best_nodes_list), best_metric



class BestNodeHillClimbing(BestPointsBase):
    '''
        Поиск лучшего узла графа с использованием алгоритма скалолаза (hill clinbing). 
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
                 all_nodes: bool=False,
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
        `all_nodes`: bool=False
            Если True рассматриваются все узлы смежные с рассчитываемым узлом.
            Если False - только исходящие.
        '''
        self.appr_val = appr_val
        self.all_nodes=all_nodes
        super().__init__(state_function, metric_function, **kwargs)

    def __call__(self,
                 env:nx.MultiDiGraph,
                 area:pd.Series=None,
                 start_node:int=None,
                 debug_route:bool=False,
                 node_calc_end_function:callable=None,
                 **kwargs):
        '''
        `env`:nx.MultiDiGraph
            Граф улично-дорожной сети
        `area`: pd.Series = None
            Маска узлов графа. Значениями True отмечены узлы графа - цели расчета леса Вороного.
            Если не указана, расчет производится для всех узлов графа.
        `start_node`: int
            Идентификатор стартового узла
        `debug_route`: bool=False
            Если True - возвращается также маршрут по которому проходил алгоритм
            в процессе поиска
        `node_calc_end_function`: callable=None
            Функция выполняемая в конце расчета каждого узла.
            
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

            if self.all_nodes:
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
            if node_calc_end_function:
                node_calc_end_function()

        if not debug_route:
            return best_node, best_metric
        else:
            return best_node, best_metric, route



class BestNodesMonkey(BestPointsBase):
    '''
        Поиск лучших узлов графа с использованием алгоритма обезьяны (monkey algorithm). 
        Могут быть возвращены только узлы из которых можно попасть в большую часть других узлов графа.
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
                 appr_val = 0.95,
                 **kwargs) -> None:
        self.appr_val = appr_val
        super().__init__(state_function, metric_function, **kwargs)

    def __call__(self, env:nx.MultiDiGraph, area=None, start_node=None, all_nodes=False, debug_route=False, **kwargs):
        '''
        Реализация: при помощи BestNodesHillClimbing ищется лучшая точка, 
        после чего обезьяна прыгает по ближайшим вершинам и вновь использует BestNodesHillClimbing.

        Так, пока не будет найден глобальный оптимум или не будет достигнуто количество итераций.
        '''
        pass