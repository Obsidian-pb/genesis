'''
Метрики параметров прибытия пожарных подразделений к зданиям
'''

import numpy as np
import pandas as pd

from genesis.core import MetricBase


class Demand(MetricBase):
    '''
    Класс-функция расчета метрики удовлетворенности спроса на услуги пожарной охраны
    '''
    def __init__(self, f=np.mean, comp_func:callable=max, zero_val=0) -> None:
        '''
        `f`: function
            Функция расчета показателя. По-умолчанию = np.mean,
            т.е. вычисляется среднее время следования.
        `comp_func`: callable
            Функция сравнения значений метрики.
            По умолчанию - лучшей считается большая.
        `zero_val`: float = 0
            Значение которое будет возвращено в случае передачи набора данных `route_times` без элементов.
        '''
        self.f = f
        self.zero_val = zero_val
        super().__init__(comp_func)

    def __call__(self, state, area=None):
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
