'''
Estimated Arrival Parameters Problem - Задача определения ожидаемых параметров реагирования пожарных подразделений

Метрики прибытия пожарных подразделений
'''

import numpy as np
import pandas as pd

from genesis.core import MetricBase







class ArrivalTime(MetricBase):
    '''
    Класс-функция расчета метрик времени первого подразделения.
    '''
    def __init__(self, f=np.mean, zero_val=0) -> None:
        '''
        `f`: function
            Функция расчета показателя. По-умолчанию = np.mean,
            т.е. вычисляется среднее время следования.
        `zero_val`: float = 0
            Значение которое будет возвращено в случае передачи набора данных `route_times` без элементов.
        '''
        self.f = f
        self.zero_val = zero_val

    def __call__(self, state):
        if not isinstance(state, (list, pd.Series)):
            raise TypeError(
                f"Аргумент times может быть только типа list или pd.Series"
                f" Имеется {type(state)}"
                )

        if len(state)==0:
            return self.zero_val
        return self.f(state)


class CoverIndex(MetricBase):
    '''
    Класс-функция расчета индекса прикрытия территорий
    '''
    def __init__(self, ip_val=10, zero_val=0) -> None:
        '''
        `ip_val`:int
            Пороговое значение для определения индекса прикрытия.
            Рекомендуется использовать 10 для городских населенных пунктов и 
            20 для сельских.
        `zero_val`: float = 0
            Значение которое будет возвращено в случае передачи набора данных 
            `route_times` без элементов.
        '''
        self.ip_val = ip_val
        self.zero_val = zero_val

    def __call__(self, state):
        if not isinstance(state, (list, pd.Series)):
            raise TypeError(
                f"Аргумент times может быть только типа list или pd.Series"
                f" Имеется {type(state)}"
                )

        # Расчет
        if len(state)==0:
            return self.zero_val
        ip_len = sum([1 for t in state if t<=self.ip_val])
        tot_len = len(state)
        return 100*ip_len/tot_len
    
    def compare(self, a, b):
        return max(a, b)

