'''
Алгоритмы решения отдельных задач
'''


import networkx as nx

from genesis.metrics import calc_node_metric




class Graphs(object):
    '''
    Алгоритмы для работы с графами

    1 Расчет центра графа
        1.1 От углов

        1.2 Пробегом от произвольной точки

        1.3 Быстрым пробегом

        1.4 Посевом

        1.5 Полным перебором
    '''
    @staticmethod
    def get_center_by_perifery(G):
        return list(G.nodes)[0]

    @staticmethod
    def get_best_node_full(G:nx.MultiDiGraph,
                           path_function=None,
                           metric_function=None,
                           weight:str='travel_time',
                           appr_val=0.95):
        '''
        Поиск лучшего узла полным перебором. 
        Могут быть возвращены только узлы из которых можно попасть в любой другой узел графа.
        Если таковых узлов нет, возвращается ошибка некорректности графа. 
        (граф должен быть проверен на корректность прежде чем будет передан функции)

        Параметры
        ---------
        `G` : MultiDiGraph
            Граф дорожной сети
        `metric_function` : function
            Функция оценки. Если не указана, используется оценка по минимальному расстоянию.
        `weight` : str
            имя поля ребер ГДС содержащего вес пути (в данном случае имеется в виду время следования)

        Возвращает
        ----------
        dict: [int, float]
            Список - [номер узла, значение метрики узла]
        '''
        if not isinstance(G, nx.MultiDiGraph):
            raise TypeError("Тип переменной G должен быть MultiDiGraph!")
        

        best_val = None
        best_node = 0

        
        for node in G.nodes():
            try:
                cur_val = calc_node_metric(G,
                            node,
                            path_function=path_function,
                            metric_function=metric_function,
                            weight=weight,
                            appr_val=appr_val)
            except ValueError:
                cur_val = best_val
            
            # if best_val:
            if not best_val or cur_val<best_val:
                best_val = cur_val
                best_node = node
            # else:
            #     best_val = cur_val
            #     best_node = node

        return best_node, best_val