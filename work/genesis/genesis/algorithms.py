'''
Алгоритмы решения отдельных задач
'''

import logging

import networkx as nx
import numpy as np
import pandas as pd

from genesis.metrics import metric_by_time
from genesis.tools import get_all_neighbor_nodes




class Graphs(object):
    '''
    Алгоритмы для работы с графами

    1 Расчет центра графа
        1.1 х Полным перебором

        1.2 х Стоком от произвольной точки
        
        1.3 Быстрым пробегом от периферии

        1.4 Посевом

    '''
    @staticmethod
    def get_best_nodes_full(G:nx.MultiDiGraph,
                            node_metric_function=None,
                            possible_nodes=None,
                            reduce=True,
                            event_after_node_calc=None,
                            return_single=False,
                            **kwargs):
        '''
        Поиск лучших узлов полным перебором. 
        Могут быть возвращены только узлы из которых можно попасть в любой другой узел графа.
        Если таковых узлов нет, возвращается ошибка некорректности графа. 
        (граф должен быть проверен на корректность прежде чем будет передан функции)
        
        Узлы для которых метрика не может быть вычислена (например слабо связанные 
        с основным графом) не учитываются. 

        ## Важно
        Следует помнить, что некорректные узлы в случае их учета посредством снижения appr_val могут 
        давать искаженное представление о метриках графа. При этом в реальности граф дорожной сети 
        как правило изобилует слабосвязанными узлами, поэтому учет только узлов обеспечивающих 100%
        достижимость всего графа может приводить к принципиальной невозможности расчета.

        ## Параметры
        `G` : MultiDiGraph
            Граф дорожной сети
        `path_function` : function
            Функция расчета пути вида nx.multi_source_dijkstra_path_length 
            - расчет от множества узлов.
        `metric_function` : function
            Функция оценки. Если не указана, используется оценка по минимальному расстоянию.
        `weight` : str
            имя поля ребер ГДС содержащего вес пути (в данном случае имеется в виду время следования)
        `appr_val`: = 0.95
            Доля узлов графа, покрытие которой считается приемлемой для принятия расчетной метрики. 
            Если при расчете метрик, из стартового узла (узлов) достижимо меньшее количество узлов,
            то такой узел не рассматривается.
        `possible_nodes`:list=None
            Если указано, то рассматриваются только переданные узлы.
        `reduce` : bool = True
            Если True - при сравнении значений метрик выбирается меньшее значение, иначе большее. 
            При расчете метрик для которых чем меньше значение тем лучше (среднее, максимальное 
            время и т.д.) необходимо использовать reduce=True, 
            при расчете метрик для которых чем больше тем лучше (ИП) - True

        ## Возвращает
        tuple: (list(int), float)
            Множество - (идентификатор узла, значение метрики узла)
        '''
        if not isinstance(G, nx.MultiDiGraph):
            raise TypeError("Тип переменной G должен быть MultiDiGraph!")


        best_val = None
        best_node = None

        if not possible_nodes:
            possible_nodes = list(G.nodes())

        for node in possible_nodes:
            try:
                # Вычисление метрики для узла
                cur_val = node_metric_function(node)
                correct=True
            except ValueError:
                cur_val = best_val
                correct=False

            # Если узел приемлем (т.е. из него можно достичь приемлемое количество прочих 
            # узлов графа)
            if correct:
                # Если лучший узел еще не определен, устанавливаем его для текущего узла
                if best_val is None and not cur_val is None:
                    best_val = cur_val
                    best_node = []

                if not best_val is None and not cur_val is None:
                    if cur_val==best_val:
                        best_node+=[node]
                    if reduce and cur_val<best_val:
                        # Если требуется поиск наименьшей метрики
                        best_val = cur_val
                        best_node = [node]
                    if not reduce and cur_val>best_val:
                        # Если требуется поиск наибольшей метрики
                        best_val = cur_val
                        best_node = [node]

            # Если указано событие которое должно происходить после расчета каждого узла 
            # - выполняем его
            if event_after_node_calc:
                event_after_node_calc()
                
        if return_single:
            return best_node[0], best_val
        else:
            return best_node, best_val


    @staticmethod
    def get_best_node_drain(G:nx.MultiDiGraph,
                            node_metric_function=None,
                            start_node=None,
                            reduce=True,
                            all_nodes=False,
                            debug_route=False,
                            **kwargs
                           ):
        '''
        Поиск лучшего узла с использованием алгоритма водостока.

        '''

        if not isinstance(G, nx.MultiDiGraph):
            raise TypeError("Тип переменной G должен быть MultiDiGraph!")

        nodes_metric = {}
        route={}

        if start_node is None:
            # Поиск первого узла из которого можно попасть во все остальные узлы ГДС !ВАЖНО! 
            # Иначе можно оказаться в тупике из которого нет выхода
            cur_val = None
            i=0
            nodes_list = list(G.nodes())
            while cur_val is None:
                if i>=G.number_of_nodes():
                    raise ValueError('Определить наиболее выгодный стартовый узел невозможно, ' \
                    'в связи с неприемлемой несвязностью графа')
                start_node = nodes_list[i]
                try:
                    logging.error('Здесь заменить на входящий граф')
                    cur_val = node_metric_function(sources=start_node, g=G)
                except ValueError:
                    cur_val = None
                nodes_metric[start_node] = cur_val
                i+=1
        else:
            # Использование переданного стартового узла
            if not isinstance(start_node,int):
                raise TypeError('Тип данных start_node должен быть только int!')
            try:
                cur_val = node_metric_function(sources=start_node, g=G)
            except ValueError:
                cur_val = None
            nodes_metric[start_node] = cur_val
            if cur_val==None:
                raise ValueError('Указанный стартовый узел неприемлем, в связи с его слабой ' \
                    'связностью с остальной частью графа')

        route[start_node] = cur_val
        logging.debug('ПЕРВЫЙ УЗЕЛ {}, метрика {}'.format(start_node, cur_val))

        # Пошаговый поиск лучшего узла от start_node
        best_val = cur_val
        best_node = start_node
        tmp_node=None
        while best_node!=tmp_node:
            tmp_node = best_node

            if all_nodes:
                nnodes = get_all_neighbor_nodes(G, tmp_node)
            else:
                nnodes = G[tmp_node]
            for node in nnodes:
                if node in nodes_metric:
                    cur_val = nodes_metric[node]
                else:
                    try:
                        cur_val = node_metric_function(sources=node, g=G)
                    except ValueError:
                        logging.debug('УЗЕЛ {}, слабосвязан'.format(node))
                        cur_val = best_val
                    nodes_metric[node] = cur_val
                
                logging.debug('УЗЕЛ {}, метрика {}'.format(node, cur_val))

                if reduce and cur_val<best_val:
                    # Если требуется поиск наименьшей метрики
                    best_val = cur_val
                    best_node = node
                if not reduce and cur_val>best_val:
                    # Если требуется поиск наибольшей метрики
                    best_val = cur_val
                    best_node = node
            route[best_node] = best_val
            logging.debug('ЛУЧШИЙ УЗЕЛ {}, метрика {}'.format(best_node, best_val))

        if not debug_route:
            return best_node, best_val
        else:
            return best_node, best_val, route


    @staticmethod
    def get_best_node_drain_max_mean(G:nx.MultiDiGraph,
                            path_function,
                            start_node=None,
                            reduce=True,
                            all_nodes=False,
                            weight: str = "travel_time",
                            appr_val=0.95,
                            err_val=None,
                            **kwargs):
        '''
        Поиск лучшего узла с использованием алгоритма водостока.
        Оценка производится последовательно метриками np.max и np.mean

        Minimum travel time location problem - MTTLP
        '''

        # Расчет метрикой максимального времени
        calc_node_metric_function = metric_by_time(G,
                                    path_function=path_function,
                                    metric_function=np.max,
                                    weight=weight,
                                    appr_val=appr_val,
                                    err_val=err_val
                                    )
        best_node, best_val = Graphs.get_best_node_drain(G, 
                                node_metric_function=calc_node_metric_function,
                                start_node=start_node,
                                reduce=reduce,
                                all_nodes=all_nodes
                                )
        logging.debug('ПЕРВЫЙ УЗЕЛ {}, метрика max {}'.format(best_node, best_val))
        # Расчет метрикой среднего времени
        calc_node_metric_function = metric_by_time(G,
                                    path_function=path_function,
                                    metric_function=np.mean,
                                    weight=weight,
                                    appr_val=appr_val,
                                    err_val=err_val
                                    )
        best_node, best_val = Graphs.get_best_node_drain(G, 
                                node_metric_function=calc_node_metric_function,
                                start_node=best_node
                                )
        logging.debug('ЛУЧШИЙ УЗЕЛ {}, метрика mean {}'.format(best_node, best_val))
        return best_node, best_val



    @staticmethod
    def calc_route_times_best_for_each(G:nx.MultiDiGraph,
                            sources:list|dict,
                            path_function,
                            weight: str = 'travel_time',
                            route_name = 'route_time',
                            nearest_name = 'nearest',
                            cutoff=None,
                            ):
        '''
        Алгоритм расчета времен прибытия в узлы графа из ближайшего стартового узла.

        # Аргументы
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
        `weight`:str или function  = "travel_time"
            Имя поля содержащего вес ребер, или функция позволяющая вычислять 
            вес динамически.
        `route_name`:str='route_time'
            Имя атрибута в котором будет сохранено время следования по маршруту
        `nearest_name` = 'nearest'
            Имя атрибута в котором будет сохранен идентификатор ближайшего стартового узла
        `cutoff`:int=None
            Ограничение расчета
        '''

        # Проверка типов входящих данных
        if isinstance(sources, list):
            if isinstance(sources, list):
                if len(sources)==0:
                    raise ValueError('В sources нет ни одного элемента!')
                for element in sources:
                    if not isinstance(element, int):
                        raise TypeError("Все идентификаторы узлов в списке sources должны иметь тип данных int!")
                    if not element in G.nodes():
                        raise KeyError(f"Узел {element} отсутствует в графе G")
        elif isinstance(sources, dict):
            if len(sources)==0:
                raise ValueError('В sources нет ни одного элемента!')
            for node, name in sources.items():
                if not isinstance(name, str):
                    raise TypeError("Все имена узлов в словаре sources должны иметь тип данных str!")
                if not node in G.nodes():
                    raise KeyError(f"Узел {node} отсутствует в графе G")
        else:
            raise TypeError("Идентификатор узла должен иметь тип данных int или list(int)!")
        if not isinstance(G, nx.MultiDiGraph):
            raise TypeError("Аргумент G должен иметь тип nx.MultiDiGraph!")


        # Расчет
        times, routes = path_function(G, sources=sources, cutoff=cutoff, weight=weight)
        times = pd.Series(times)
        if isinstance(sources, dict):
            nearest = pd.Series({k:sources[route[0]] for k, route in routes.items()}, dtype=str)
        else:
            nearest = pd.Series({k:route[0] for k, route in routes.items()}, dtype='int64')

        # Установка результатов расчета в качестве атрибутов ребер
        nx.set_node_attributes(G, times, route_name)
        nx.set_node_attributes(G, nearest, nearest_name)


    @staticmethod
    def calc_route_times_each_for_each(G:nx.MultiDiGraph,
                            sources:list|dict,
                            path_function,
                            weight: str = 'travel_time',
                            routes_times_name='routes_times',
                            cutoff=None,
                            event_after_source_calc=None,
                            cover_count_name=None
                            ):
        '''
        Алгоритм расчета времен прибытия в узлы графа из всех стартовых узлов во все узлы графа.

        # Аргументы
        `sources`:list|dict
            Стартовые узлы. Может быть списком узлов вида list(int), или словарем вида dict(int:str), где ключ - 
            идентификатор узла, значение - его наименование. Может использоваться для указания узлов в которых 
            расположены пожарные подразделения: {1234:'ПСЧ-1'}
        `path_function`: function
            Функция расчета кратчайших путей от единственного источника. 
            В качестве функции могут быть переданы реализации алгоритмов из пакета
            `networkx`. Например, реализация алгоритма Дейкстры: `nx.single_source_dijkstra_path_length`.
            Пользователь может использовать собственные функции с
            интерфейсом `func(G: Graph, source: Any, cutoff: Any | None = None, weight: str = "weight")`
        `weight`:str или function  = "travel_time"
            Имя поля содержащего вес ребер, или функция позволяющая вычислять 
            вес динамически.
        `cutoff`:int=None
            Ограничение расчета
        `each_to_each`:bool=False
            Если False - будет определена длина  маршрута до каждого узла графа только из ближайшего стартового узла.
            Если True - будет определена длина маршрута от каждого стартового узла в каждый узел графа.
            Может быть использовано в том числе для определения времени следования в каждый узел. 
        `each_to_each_pattern`:str='node_{}'
            Если each_to_each=True, с таким шаблоном будут сохранены имена полей для каждого из стартовых узлов.
            В {} будет добавлен идентификатор узла или его имя, если тип sources=dict.
        '''

        # Проверка типов входящих данных
        if isinstance(sources, list):
            if isinstance(sources, list):
                if len(sources)==0:
                    raise ValueError('В sources нет ни одного элемента!')
                for element in sources:
                    if not isinstance(element, int):
                        raise TypeError("Все идентификаторы узлов в списке sources должны иметь тип данных int!")
                    if not element in G.nodes():
                        raise KeyError(f"Узел {element} отсутствует в графе G")
        elif isinstance(sources, dict):
            if len(sources)==0:
                raise ValueError('В sources нет ни одного элемента!')
            for node, name in sources.items():
                if not isinstance(name, str):
                    raise TypeError("Все имена узлов в словаре sources должны иметь тип данных str!")
                if not node in G.nodes():
                    raise KeyError(f"Узел {node} отсутствует в графе G")
        else:
            raise TypeError("Идентификатор узла должен иметь тип данных int или list(int)!")
        if not isinstance(G, nx.MultiDiGraph):
            raise TypeError("Аргумент G должен иметь тип nx.MultiDiGraph!")
        if isinstance(cutoff, list):
            if len(cutoff)!=len(sources):
                raise ValueError("Количество элементов в списке cutoff должно соответствовать количеству элементов в sources!")


        # Расчет
        arrivals = {k:{} for k in G.nodes()}
        for start_node in sources:
            times = path_function(G, source=start_node, cutoff=cutoff, weight=weight)
            if isinstance(sources, dict):
                route_name_cur = sources[start_node]
            else:
                route_name_cur = start_node
            for k,v in times.items():
                arrivals[k][route_name_cur] = v
            # Если указано событие которое должно происходить после расчета каждого узла - выполняем его
            if event_after_source_calc:
                event_after_source_calc()

        # Установка результатов расчета в качестве атрибутов ребер
        if isinstance(routes_times_name, str):
            nx.set_node_attributes(G, arrivals, routes_times_name)
        if isinstance(cover_count_name, str):
            nx.set_node_attributes(G, {k:len(a) for k,a in arrivals.items()}, cover_count_name)


# class MCLP(object):
#     '''
#     Класс для решения задач размещения класса MCLP
#     '''
#     @staticmethod
#     def mclp_step_by_step(G:nx.MultiDiGraph, 
#                             flex_locations, 
#                             best_node_function,
#                             path_function,
#                             weight: str = 'travel_time',
#                             route_name = 'route_time',
#                             nearest_name = 'nearest',
#                             cutoff=None,
#                             static_locations=None,
#                             reduce=True,
#                             all_nodes=False,
#                             event_after_step_calc=None):
#         '''
#         Алгоритм решения задачи MCLP методом пошаговых приближений.
#         '''

#         Graphs.calc_route_times_best_for_each(G, )