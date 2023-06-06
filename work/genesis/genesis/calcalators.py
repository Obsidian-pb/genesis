'''
Различные расчетные функции.
'''

import networkx as nx
from .models import Environment
from . import settings

class Metrics(object):
    '''
    Функции расчета метрик.
    '''
    @staticmethod
    def metric_calc(E:Environment, node:int, func=None, weight: str = "weight"):
        '''
        Возвращает значение стандартной целевой метрики.

        Аргументы
        ---------
        `E`:Environment, 
            Окружение.
        
        `node`:int
            Узел для которого производится расчет

        `func`: function
            Целевая функция расчета метрики. По-умолчанию - max.
        
        `weight`:str или function
            Имя поля содержащего вес ребер, или функция позволяющая вычислять вес динамически.

        Возвращает
        ----------
        `metric_val`: float
            Значение целевой метрики
        '''
        if not isinstance(E, Environment):
            raise TypeError("Аргумент E должен быть моделью окружения!") 
        if not isinstance(node, int):
            raise TypeError("Идентификатор узла должен иметь тип данных int!")
        if not node in E.G.nodes():
            raise Exception(f"Узел {node} отсутствует в графе G")
        
        route_lens = settings.ssfpl(E.G, node, weight=weight)      

        if func==None:
            return max(route_lens.values())
        else:
            return func(list(route_lens.values()))

    @staticmethod
    def ip_calc(route_lens:list, ip_val=10, rv=2):
        '''
        Расчет индекса прикрытия.


        '''
        tot_len = len(route_lens)
        ip_len = sum(route_lens<=ip_val)
        return round(100*ip_len/tot_len, rv)




# Устаревшее
def max_time(G:nx.MultiDiGraph, node:int, weight: str = "weight"):
    '''
    Возвращает протяженность маршрута от заданного узла до наиболее удаленного от нее

    Аргументы
    ---------
    `G`:nx.MultiDiGraph, 
        Граф дорожной сети
    
    `node`:int
        Узел для которого производится расчет

    `weight`:str или function
        Имя поля содержащего вес ребер, или функция позволяющая вычислять вес динамически.

    Возвращает
    ----------
    `max_time`: float
        Протяженность маршрута от заданного узла до наиболее удаленного от нее, 
        с учетом веса ребер маршрута
    '''
    raise Warning("Функция устарела! Не рекомендуется ее использовать!")
    return metric_calc(G, node, weight=weight)