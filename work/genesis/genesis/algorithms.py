'''
Алгоритмы решения отдельных задач
'''


import networkx as nx
import numpy as np

from genesis.metrics import metric_by_time
from genesis.tools import get_all_neighbour_nodes

import logging



class Graphs(object):
    '''
    Алгоритмы для работы с графами

    1 Расчет центра графа
        1.1 Полным перебором

        1.2 Пробегом от произвольной точки
        
        1.3 От периферии

        1.4 Быстрым пробегом

        1.5 Посевом

    '''
    @staticmethod
    def get_best_node_full(G:nx.MultiDiGraph,
                           node_metric_function=None,
                           possible_nodes=None,
                           reduce=True):
        '''
        Поиск лучшего узла полным перебором. 
        Могут быть возвращены только узлы из которых можно попасть в любой другой узел графа.
        Если таковых узлов нет, возвращается ошибка некорректности графа. 
        (граф должен быть проверен на корректность прежде чем будет передан функции)
        
        Узлы для которых метрика не может быть вычислена (например слабо связанные с основным графом) 
        не учитываются. 

        ## Важно
        Следует помнить, что некорректные узлы в случае их учета посредством снижения appr_val могут 
        давать искаженное представление о метриках графа. При этом в реальности граф дорожной сети 
        как правило изобилует слабосвязными узлами, поэтому учет только узлов обеспечивающих 100%
        достижимость всего графа может приводить к принципиальной невозможности расчета.

        ## Параметры
        `G` : MultiDiGraph
            Граф дорожной сети
        `path_function` : function
            Функция расчета пути вида nx.multi_source_dijkstra_path_length - расчет от множества узлов.
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
            При расчете метрик для которых чем меньше значение тем лучше (среднее, максимальное время и т.д.) 
            необходимо использовать reduce=True, 
            при расчете метрик для которых чем больше тем лучше (ИП) - True

        ## Возвращает
        tuple: (int, float)
            Множестов - (идентификатор узла, значение метрики узла)
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
            except ValueError:
                cur_val = best_val
            
            # Если лучший узел еще не определен, устанавливаем его для текущего узла
            if best_val==None and not cur_val==None:
                best_val = cur_val
                best_node = node
            
            if not best_val==None and not cur_val==None:
                if reduce and cur_val<best_val:
                    # Если требуется поиск наименьшей метрики
                    best_val = cur_val
                    best_node = node
                if not reduce and cur_val>best_val:
                    # Если требуется поиск наибольшей метрики
                    best_val = cur_val
                    best_node = node

        logging.warning('Должен возвращаться список!')
        return best_node, best_val
    

    @staticmethod
    def get_best_node_drain(G:nx.MultiDiGraph,
                            node_metric_function=None,
                            start_node=None,
                            reduce=True,
                            all_nodes=False,
                           ):
        '''
        Поиск лучшего узла с использованием алгоритма водостока.

        '''

        if not isinstance(G, nx.MultiDiGraph):
            raise TypeError("Тип переменной G должен быть MultiDiGraph!")
        
        nodes_metric = {}
        route={}

        if start_node==None:
            # Поиск первого узла из которого можно попасть во все остальные узлы ГДС !ВАЖНО! Иначе можно оказаться в тупике из которого нет выхода
            cur_val = None
            i=0
            nodes_list = list(G.nodes())
            while cur_val==None:
                if i>=G.number_of_nodes():
                    raise ValueError('Определить наиболее выгодный стартовый узел невозможно, в связи с неприемлемой несвязностью графа')
                start_node = nodes_list[i]
                try:
                    cur_val = node_metric_function(start_node)
                except ValueError:
                    cur_val = None
                nodes_metric[start_node] = cur_val
                i+=1
        else:
            # Использование переданного стартового узла
            if not isinstance(start_node,int):
                raise TypeError('Тип данных start_node должен быть только int!')
            try:
                cur_val = node_metric_function(start_node)
            except ValueError:
                cur_val = None
            nodes_metric[start_node] = cur_val
            if cur_val==None:
                raise ValueError('Указанный стартовый узел неприемлем, в связи с его слабой связностью с остальной частью графа')

        route[start_node] = cur_val
        logging.debug(f'ПЕРВЫЙ УЗЕЛ {start_node}, метрика {cur_val}')

        # Пошаговый поиск лучшего узла от start_node
        best_val = cur_val
        best_node = start_node
        tmp_node=None
        while best_node!=tmp_node:
            tmp_node = best_node

            if all_nodes:
                nnodes = get_all_neighbour_nodes(G, tmp_node)
            else:
                nnodes = G[tmp_node]
            for node in nnodes:
                if node in nodes_metric.keys():
                    cur_val = nodes_metric[node]
                else:
                    try:
                        cur_val = node_metric_function(node)
                    except ValueError:
                        logging.debug(f'УЗЕЛ {node}, слабосвязан')
                        cur_val = best_val
                    nodes_metric[node] = cur_val
                
                logging.debug(f'УЗЕЛ {node}, метрика {cur_val}')

                if reduce and cur_val<best_val:
                    # Если требуется поиск наименьшей метрики
                    best_val = cur_val
                    best_node = node
                if not reduce and cur_val>best_val:
                    # Если требуется поиск наибольшей метрики
                    best_val = cur_val
                    best_node = node
            route[best_node] = best_val
            logging.debug(f'ЛУЧШИЙ УЗЕЛ {best_node}, метрика {best_val}')

        logging.warning('Должен возвращаться список!')
        return best_node, best_val, route

    @staticmethod
    def get_best_node_drain_max_mean(G:nx.MultiDiGraph,
                            path_function,
                            start_node=None,
                            reduce=True,
                            all_nodes=False,
                            weight: str = "travel_time",
                            appr_val=0.95,
                            err_val=None):
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
        best_node, best_val, _ = Graphs.get_best_node_drain(G, 
                                node_metric_function=calc_node_metric_function,
                                start_node=start_node,
                                reduce=reduce,
                                all_nodes=all_nodes
                                )
        logging.debug(f'ПЕРВЫЙ УЗЕЛ {best_node}, метрика max {best_val}')
        # Расчет метрикой среднего времени
        calc_node_metric_function = metric_by_time(G,
                                    path_function=path_function,
                                    metric_function=np.mean,
                                    weight=weight,
                                    appr_val=appr_val,
                                    err_val=err_val
                                    )
        best_node, best_val, _ = Graphs.get_best_node_drain(G, 
                                node_metric_function=calc_node_metric_function,
                                start_node=best_node
                                )
        logging.debug(f'ЛУЧШИЙ УЗЕЛ {best_node}, метрика mean {best_val}')
        return best_node, best_val
