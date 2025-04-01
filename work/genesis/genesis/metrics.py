'''
Estimated Arrival Parameters Problem - Задача определения ожидаемых параметров реагирования пожарных подразделений

Метрики прибытия пожарных подразделений
'''

import numpy as np
import pandas as pd

from .core import MetricBase







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
        super().__init__()

    def __call__(self, state, area=None):
        '''
        `state` (`состояние`): pd.Series
            Серия времен прибытия в разные точки окружения.

        `area`: pd.Series
            Серия данных содержащих маску точек которые должны быть учтены при расчете метрики.
        '''

        if not isinstance(state, (list, pd.Series)):
            raise TypeError(
                f"Аргумент times может быть только типа list или pd.Series"
                f" Имеется {type(state)}"
                )

        # Отбор узлов по area (списку узлов которые следует учесть в расчете)
        if not area is None:
            if isinstance(state, pd.Series):
                state_c = state.loc[area]
            else:
                state_c = [x for x in state if x in area]
        else:
            state_c = state

        if len(state_c)==0:
            return self.zero_val
        return self.f(state_c)


class CoverIndex(MetricBase):
    '''
    Класс-функция расчета индекса прикрытия территорий

    ВНИМАНИЕ: Данная метрика рассчитывается только для тех узлов в которые можно попасть.
    Для расчета исходя из количества всех узлов графа следует использовать fire_units.CoverIndexBuilding
    А позже metrics.CoverIndexPoints
    '''
    def __init__(self, ip_val:int=10, zero_val:float=0, comp_func:callable=max, tot_len:int=None) -> None:
        '''
        `ip_val`:int
            Пороговое значение для определения индекса прикрытия.
            Рекомендуется использовать 10 для городских населенных пунктов и 
            20 для сельских.
        `zero_val`: float = 0
            Значение которое будет возвращено в случае передачи набора данных 
            `route_times` без элементов.
        `comp_func`: callable
            Функция сравнения значений метрики
        `tot_len`: int = None
            Общее количество объектов (например узлов) рассматриваемых при расчете
        '''
        self.ip_val = ip_val
        self.zero_val = zero_val
        self.tot_len = tot_len
        super().__init__(comp_func)

    def __call__(self, state, area=None):
        '''
        `state` (`состояние`): pd.Series
            Серия времен прибытия в разные точки окружения.

        `area`: pd.Series
            Серия данных содержащих маску точек которые должны быть учтены при расчете метрики.
        '''
        
        if not isinstance(state, (list, pd.Series)):
            raise TypeError(
                f"Аргумент times может быть только типа list или pd.Series"
                f" Имеется {type(state)}"
                )

        # Отбор узлов по area (списку узлов которые следует учесть в расчете)
        if not area is None:
            if isinstance(state, pd.Series):
                state_c = state.loc[area]
            else:
                state_c = [x for x in state if x in area]
        else:
            state_c = state

        # Расчет
        if len(state_c)==0:
            return self.zero_val
        ip_len = sum([1 for t in state_c if t<=self.ip_val])
        if self.tot_len is None:
            tot_len = len(state_c)
        else:
            tot_len = self.tot_len
        return 100*ip_len/tot_len
