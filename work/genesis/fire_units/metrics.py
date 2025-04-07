'''
Метрики параметров прибытия пожарных подразделений к зданиям
'''

import numpy as np
import pandas as pd
import geopandas as gpd

from genesis.metrics import ArrivalTime

try:
    from ..genesis.core import MetricBase
except:
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
        if not buildings_node_id_field in buildings.columns:
            raise KeyError(f"Поле `{buildings_node_id_field}` отсутствует в 'buildings'")
        if not buildings_demand_field in buildings.columns:
            raise KeyError(f"Поле `{buildings_demand_field}` отсутствует в 'buildings'")

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
        buildings_s = self.buildings.query(f'{self.buildings_node_id_field} in @state_c.keys()')
        merged_df = pd.merge(buildings_s,
                             state_c,
                             how='left',
                             left_on=self.buildings_node_id_field,
                             right_index=True)

        # Расчет собственно состояния удовлетворенности спроса
        return self.f(merged_df[self.buildings_demand_field] / merged_df['times'])




class CoverIndexBuilding(MetricBase):
    '''
    Класс-функция расчета индекса прибытия к зданиям
    '''
    def __init__(self,
                 buildings,
                #  f:callable = np.mean,
                 comp_func:callable = max,
                 zero_val=0,
                 ip_val=10,
                 buildings_node_id_field: str = 'node',
                #  buildings_demand_field: str = 'demand',
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
        if not buildings_node_id_field in buildings.columns:
            raise KeyError(f"Поле `{buildings_node_id_field}` отсутствует в 'buildings'")

        self.buildings = buildings
        # self.f = f
        self.zero_val = zero_val
        self.buildings_node_id_field = buildings_node_id_field
        # self.buildings_demand_field = buildings_demand_field
        self.ip_val = ip_val
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
        buildings_s = self.buildings.query(f'{self.buildings_node_id_field} in @state_c.keys()')
        merged_df = pd.merge(buildings_s,
                             state_c,
                             how='left',
                             left_on=self.buildings_node_id_field,
                             right_index=True)
        # Расчет
        state_c = merged_df['times']
        if len(state_c)==0:
            return self.zero_val
        # ip_len = sum([1 for t in state_c if t<=self.ip_val])
        ip_len = sum(state_c <= self.ip_val)
        tot_len = len(state_c)

        return 100*ip_len/tot_len


        # # Расчет собственно состояния удовлетворенности спроса
        # return merged_df['times']


class ArrivalTimeBuilding(MetricBase):
    '''
    Класс-функция расчета времени прибытия к зданиям
    '''
    def __init__(self,
                 buildings,
                 f:callable = np.mean,
                 comp_func:callable = min,
                 zero_val=1000,
                 buildings_node_id_field: str = 'node',
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
        `buildings_demand_field`: str = 'demand'
            Имя поля в `buildings` содержащего значения спроса
        '''
        if not buildings_node_id_field in buildings.columns:
            raise KeyError(f"Поле `{buildings_node_id_field}` отсутствует в 'buildings'")

        self.buildings = buildings
        self.f = f
        self.zero_val = zero_val
        self.buildings_node_id_field = buildings_node_id_field
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
        buildings_s = self.buildings.query(f'{self.buildings_node_id_field} in @state_c.keys()')
        merged_df = pd.merge(buildings_s,
                             state_c,
                             how='left',
                             left_on=self.buildings_node_id_field,
                             right_index=True)
        # Расчет
        state_c = merged_df['times']
        if len(state_c)==0:
            return self.zero_val

        return self.f(state_c)


class CoverIndexValue(MetricBase):
    '''
    Класс-функция расчета взвешенного индекса прикрытия.
    Подходит для расчета индекса прикрытия населенных пунктов 
    в зависимости от численности их населения
    '''
    def __init__(self,
                 data: gpd.GeoDataFrame,
                #  f:callable = np.mean,
                 value_field: str,
                 comp_func:callable = max,
                 zero_val = 0,
                 ip_val = 10,
                 data_node_id_field: str = 'node',
                 ) -> None:
        '''
        `data`: pd.GeoDataFrame
            Геодатафрейм со сведениями о зданиях.
        `f`: callable
            Функция расчета показателя. По-умолчанию = np.mean,
            т.е. вычисляется среднее время следования.
        `comp_func`: callable
            Функция сравнения значений метрики.
            По умолчанию - лучшей считается большая.
        `zero_val`: float = 0
            Значение которое будет возвращено в случае передачи набора данных `route_times` без элементов.
        `value_field`: str = None
            Имя поля в `data` содержащего вес (например численность населения).
        `data_node_id_field`: str = 'node'
            Имя поля в `data` содержащего идентификаторы узлов.
        '''
        if not value_field in data.columns:
            raise KeyError(f"Поле `{value_field}` отсутствует в 'buildings'")

        self.data = data
        self.value_field = value_field
        self.zero_val = zero_val
        self.ip_val = ip_val
        self.data_node_id_field = data_node_id_field
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

        if len(state_c) == 0:
            return self.zero_val

        # Объединение данных об узлах и временах прибытия в каждый из них
        data_s = self.data.query(f'{self.data_node_id_field} in @state_c.keys()')
        merged_df = pd.merge(data_s,
        # merged_df = pd.merge(self.data,
                             state_c,
                             how='left',
                             left_on = self.data_node_id_field,
                             right_index = True)
        
        # Расчет полного веса по всему набору данных
        total_value = merged_df[self.value_field].sum()
        
        # Оставляем только строки для узлов в которые время прибытия меньше или равно 10 минут
        merged_df = merged_df[merged_df['times'] <= self.ip_val]
        

        # Если таких узлов нет - возвращаем значение для ноля
        if len(merged_df) == 0:
            return self.zero_val
        

        return 100 * merged_df[self.value_field].sum() / total_value