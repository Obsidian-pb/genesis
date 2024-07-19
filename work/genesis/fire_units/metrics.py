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
    def __init__(self,
                 buildings,
                 f:callable = np.mean,
                 comp_func:callable = max,
                 zero_val=0,
                 buildings_node_id_field: str = 'node',
                 buildings_demand_field: str = 'demand',
                 ) -> None:
        '''
        `buildings`: pd.GeoDataFrame
            Геодатафрейм со сведениями о зданиях.
        `f`: callable
            Функция расчета показателя. По-умолчанию = np.mean,
            т.е. вычисляется среднее время следования.
        `comp_func`: callable
            Функция сравнения значений метрики.
            По умолчанию - лучшей считается большая.
        `zero_val`: float = 0
            Значение которое будет возвращено в случае передачи набора данных `route_times` без элементов.
        `buildings_node_id_field`: str = 'node'
            Имя поля в `buildings` содержащего идентификаторы узлов.
        buildings_demand_field: str = 'demand'
            Имя поля в `buildings` содержащего значения спроса
        '''
        self.buildings = buildings
        self.f = f
        self.zero_val = zero_val
        self.buildings_node_id_field = buildings_node_id_field
        self.buildings_demand_field = buildings_demand_field
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
                f"Аргумент state может быть только типа list или pd.Series"
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
        
        # Расчет метрики по спросу
        merged_df = pd.merge(self.buildings,
                             state_c,
                             left_on=self.buildings_node_id_field,
                             right_index=True)

        # Расчет собственно состояния удовлетворенности спроса
        return self.f(merged_df[self.buildings_demand_field] / merged_df['times'])  #, merged_df['nearest']   #, merged_df['times']

        # return self.f(state_c)
