'''
Различные расчетные функции.
'''

import pandas as pd
# import networkx as nx
from .models import Environment
# from . import swiss_knife as knife
# from .swiss_knife import ssfpl


class Metrics(object):
    '''
    Функции расчета метрик.
    '''
    @staticmethod
    def calc_metric(E:Environment, 
                    node:int, 
                    path_function, 
                    metric_function, 
                    weight: str = "weight",
                    precision: int = 2):
        '''
        Базовая функция расчета метрик.
        Возвращает значение стандартной целевой метрики.
        Может быть использована как интерфейс для разработки более специализированных функций.

        Аргументы
        ---------
        `E`:Environment, 
            Окружение.
        
        `node`:int
            Узел для которого производится расчет

        `path_function`: function
            Функция расчета кратчайших путей

        `metric_function`: function
            Целевая функция расчета метрики.
        
        `weight`:str или function
            Имя поля содержащего вес ребер, или функция позволяющая вычислять 
            вес динамически.

        `precision`: int 
            Точность округления

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
            raise KeyError(f"Узел {node} отсутствует в графе G")

        route_lens = path_function(E.G, node, weight=weight)

        try:
            val = metric_function(pd.Series(route_lens))
            return round(val, precision)
        except Exception as exc:
            raise TypeError(
                "Данный тип функций не применим для аргумента с типом Series"
                ) from exc

    @staticmethod
    def calc_ip(route_times:pd.Series, 
                ip_val=10,
                precision: int = 2):
        '''
        Расчет индекса прикрытия.

        Аргументы
        ---------
        `route_times`:pd.Series
            Серия данных о временах прибытия в узлы ГДС 
            (или вообще произвольных данных о временах прибытия)

        `ip_val`:int
            Пороговое значение для определения индекса прикрытия.
            Рекомендуется использовать 10 для городских населенных пунктов и 
            20 для сельских.
        
        `precision`: int 
            Точность округления
        
        Возвращает
        ----------
        `metric_val`: float
            Значение целевой метрики
        '''
        if not isinstance(route_times, pd.Series):
            raise TypeError("Аргумент route_times может быть только типа pd.Series")

        tot_len = len(route_times)
        if tot_len==0:
            return 0
        ip_len = sum(route_times<=ip_val)
        return round(100*ip_len/tot_len, precision)

    # @staticmethod
    # def calc_common():

