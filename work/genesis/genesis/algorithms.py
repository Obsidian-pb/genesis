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
        У злы для которых метрика не может быть вычислена (например слабо связанные с основным графом) 
        не учитываются.

        Параметры
        ---------
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

        Возвращает
        ----------
        dict: [int, float]
            Список - [идентификатор узла, значение метрики узла]
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
            # else:
            # if not cur_val==None:
            if not best_val==None and not cur_val==None:
                if reduce and cur_val<best_val:
                    best_val = cur_val
                    best_node = node
                if not reduce and cur_val>best_val:
                    best_val = cur_val
                    best_node = node


        return best_node, best_val