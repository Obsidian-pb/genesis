''' 


''' 
# print('__file__={0:<35} | __name__={1:<25} | __package__={2:<25}'.format(__file__,__name__,str(__package__)))

import networkx as nx
from .calcalators import calc_max


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
    def get_best_node_full(G:nx.MultiDiGraph, func=None, weight:str='weight'):
        '''
        Поиск лучшего узла полным перебором. 
        Могут быть возвращены только узлы из которых можно попасть в любой другой узел графа.
        Если таковых узлов нет, возвращается ошибка некорректности графа. 
        (граф должен быть проверен на корректность прежде чем будет передан функции)

        Параметры
        ---------
        `G` : MultiDiGraph
            Граф дорожной сети
        `func` : function
            Функция оценки. Если не указана, используется оценка минимальному расстоянию.
        `weight` : str
            имя поля ребер ГДС содержащего вес пути (в данном случае имеется в виду время следования)

        Возвращает
        ----------
        dict: [int, float]
            Список - [номер узла, значение метрики узла]
        '''
        if not isinstance(G, nx.MultiDiGraph):
            raise TypeError("Тип переменной G должен быть мультидиграф (MultiDiGraph)!")
        

        best_val = 100000
        best_node = 0
        
        for node in G.nodes():
            lngs = nx.single_source_dijkstra_path_length(G, node)
            if len(lngs)==G.number_of_nodes():
                max_val = max(lngs.items(), key = lambda x: x[1])
                if max_val[1]<best_val:
                    best_val = max_val[1]
                    best_node = node

        return best_node

# test:
if __name__ == "__main__":
    print("ok")

