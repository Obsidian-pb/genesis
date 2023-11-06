'''
Алгоритмы решения отдельных задач
'''


import networkx as nx

from genesis.metrics import calc_node_metric




class Graphs(object):
    '''
    Алгоритмы для работы с графами

    1 Расчет центра графа
        1.1 Полным перебором

        1.2 Пробегом от произвольной точки
        
        1.3 От углов

        1.4 Быстрым пробегом

        1.5 Посевом

    '''
    @staticmethod
    def get_best_node_full(G:nx.MultiDiGraph,
                           path_function=None,
                           metric_function=None,
                           weight:str='travel_time',
                           appr_val=0.95,
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
                cur_val = calc_node_metric(G,
                            node,
                            path_function=path_function,
                            metric_function=metric_function,
                            weight=weight,
                            appr_val=appr_val)
            except ValueError:
                cur_val = best_val
            
            if best_val==None and not cur_val==None:
                best_val = cur_val
                best_node = node
            
            if not best_val==None and not cur_val==None:
                if reduce and cur_val<best_val:
                    best_val = cur_val
                    best_node = node
                if not reduce and cur_val>best_val:
                    best_val = cur_val
                    best_node = node


        return best_node, best_val
    
    # @staticmethod
    # def select_best_node_in_neighbourhood(G,
    #                     node,
    #                     )

    @staticmethod
    def get_best_node_drain(G:nx.MultiDiGraph,
                           path_function=None,
                           metric_function=None,
                           weight:str='travel_time',
                           appr_val=0.95,
                           possible_nodes=None,
                           start_node=None,
                           reduce=True):
        '''
        Поиск лучшего узла с использованием алгоритма водостока.

        '''

        if not isinstance(G, nx.MultiDiGraph):
            raise TypeError("Тип переменной G должен быть MultiDiGraph!")
        
        nodes_metric = {}

        if start_node==None:
            # Поиск первого узла из которого можно попасть во все остальные узлы ГДС !ВАЖНО! Иначе можно оказаться в тупике из которого нет выхода
            cur_val = 0
            i=0
            nodes_list = list(G.nodes())
            while cur_val==0:
                if i>=G.number_of_nodes():
                    raise ValueError('Определить наиболее выгодный стартовый узел невозможно, в связи с критической несвязностью графа')
                start_node = nodes_list[i]
                cur_val = calc_node_metric(G,
                                start_node,
                                path_function=path_function,
                                metric_function=metric_function,
                                weight=weight,
                                err_val=0,
                                appr_val=appr_val)
                nodes_metric[start_node] = cur_val
                i+=1
            
            # if cur_val==0:
            #     raise ValueError('Определить наиболее выгодный стартовый узел невозможно, в связи с критической несвязностью графа')
        else:
            # Использование переданного стартового узла
            cur_val = calc_node_metric(G,
                                start_node,
                                path_function=path_function,
                                metric_function=metric_function,
                                weight=weight,
                                err_val=0,
                                appr_val=appr_val)
            nodes_metric[start_node] = cur_val
            if cur_val==0:
                raise ValueError('Указанный стартовый узел неприемлем, в связи с его слабой связностью с остальной частью графа')

        # Пошаговый поиск лучшего узла от start_node
        best_val = cur_val
        best_node = start_node
        tmp_node=None
        while best_node!=tmp_node:
            tmp_node = best_node
            for node in G[tmp_node]:
                if node in nodes_metric.keys():
                    cur_val = nodes_metric[node]
                else:
                    try:
                        cur_val = calc_node_metric(G,
                                    node,
                                    path_function=path_function,
                                    metric_function=metric_function,
                                    weight=weight,
                                    appr_val=appr_val)
                    except ValueError:
                        cur_val = best_val
                    nodes_metric[node] = cur_val
                
                if reduce and cur_val<best_val:
                    best_val = cur_val
                    best_node = node
                if not reduce and cur_val>best_val:
                    best_val = cur_val
                    best_node = node
                
        return best_node, best_val
