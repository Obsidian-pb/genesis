'''
Реализация алгоритмов гибридизации
'''






import warnings

import networkx as nx
import pandas as pd

from genesis.core import BestPointsBase, MCLPBase, MetricBase, StateBase



class Boosting(MCLPBase):
    '''
    Реализация базового алгоритма MCLP как гибрида

    Является функцией гибридизации алгоритмов BestPoints, MCLP и LSCP,
    методом бустинга, т.е. последовательного выполнения функций и передачи полученного 
    результата далее.
    '''
    def __init__(self,
                 functions: list,
                 state_function:  StateBase      = None,
                 metric_function: MetricBase     = None,
                 function_end_function: callable =None,
                 **kwargs):

        # 0. Проверка корректности пришедших данных
        if not isinstance(functions, list):
            raise TypeError('Аргумент `functions` должен быть типа list!')
        if not isinstance(function_end_function, callable) and not function_end_function is None:
            raise TypeError('Аргумент `function_end_function` должен быть типа callable или иметь значение None!')
        if not isinstance(state_function, StateBase) and not state_function is None:
            raise TypeError('Аргумент `state_function` должен быть типа StateBase или иметь значение None!')
        if not isinstance(metric_function, MetricBase) and not metric_function is None:
            raise TypeError('Аргумент `metric_function` должен быть типа MetricBase или иметь значение None!')

        # 1. Сохранение данных в свойствах функции
        self.functions = functions
        self.function_end_function = function_end_function
        super().__init__(state_function, metric_function, **kwargs)

    
    def __call__(self,
                 env:nx.Graph,
                 dynamic_nodes: dict,
                 static_nodes: dict = None,
                 area: pd.Series = None,
                 **kwargs):
        '''
        ## Аргументы

        `env`:nx.Graph

            Граф улично-дорожной сети

        `dynamic_nodes`: dict

            Список стартовых узлов графа в которых размещены
            подразделения оптимальные места которых следует определить.

        `static_nodes`: dict = None

            Список стартовых узлов графа в которых размещены
            подразделения изменять размещение которых не следует.

        `area`: pd.Series = None

            Маска узлов графа. Значениями True отмечены узлы графа - цели расчета леса Вороного.
            Если не указана, расчет производится для всех узлов графа.

        ## Возвращает

        `best_dynamic_nodes, best_metric`: tuple[list | dict, float]

            Список или словарь лучших мест размещения, значение метрики metric_function
            для лучшего размещения.
        '''
        # 0. Проверка корректности пришедших данных
        if not isinstance(env, nx.Graph):
            raise TypeError("Тип аргумента `env` должен быть Graph!")
        if not static_nodes is None:
            if not (isinstance(dynamic_nodes,dict) and isinstance(static_nodes,dict)):
                raise TypeError(f'Аргументы `dynamic_nodes` и `static_nodes` должны быть одинакового типа: dict'
                                f'Имеют: {type(dynamic_nodes)}, {type(static_nodes)}')
        if not area is None and not isinstance(area, pd.Series):
            raise TypeError(f'Аргумент `area` должен иметь тип `pd.Series`! Имеет {type(area)}')
        if len(dynamic_nodes) <1:
            raise ValueError(f'Количество элементов `dynamic_nodes` не может быть равно 0! Сейчас {(len(dynamic_nodes) + len(static_nodes))}')

        # 1. Сбор данных о размещении в единый словарь
        if not static_nodes is None:
            best_nodes = {**dynamic_nodes, **static_nodes}
        else:
            best_nodes = dynamic_nodes

        # 2. Последовательный перебор всех функций
        for m in self.functions:
            best_nodes, metric_val = m(env           = env,
                                       area          = area,
                                       dynamic_nodes = best_nodes,
                                       **kwargs)

        # 3. Возвращаем результат
        return best_nodes, metric_val






class AdapterBLP2MCLP(MCLPBase):
    '''
    Адаптер алгоритмов BLP к MCLP.

    Позволяет использовать алгоритмы BestPointsBase как MCLPBase.
    '''

    def __init__(self,
                 blp_function:    BestPointsBase,
                 state_function:  StateBase      = None,
                 metric_function: MetricBase     = None,
                 **kwargs):
        '''
        Перечень аргументов соответствует алгоритму BLP переданному через аргумент `blp_function`.

        ## Аргументы
        
        `blp_function`: BestPointsBase
            
            функция реализующая алгоритм BLP.

        `state_function`: StateBase

            функция расчета состояния окружения

        `metric_function`: MetricBase

            Функция расчета метрики

        `**kwargs`
            
            прочие аргументы определяющиеся реализацией blp_function.
        '''
        if not isinstance(blp_function, BestPointsBase):
            raise TypeError("Аргумент `blp_function` должен иметь тип `BestPointsBase`!")
        if not isinstance(state_function, StateBase) and not state_function is None:
            raise TypeError("Аргумент `state_function` должен иметь тип `StateBase`!")
        if not isinstance(metric_function, MetricBase) and not metric_function is None:
            raise TypeError("Аргумент `metric_function` должен иметь тип `MetricBase`!")

        self.blp_function = blp_function
        super().__init__(state_function, metric_function, **kwargs)


    def __call__(self,
                 env,
                 area = None,
                 dynamic_nodes: dict = None,
                 **kwargs) -> tuple[dict, int | float]:
        '''
        # Аргументы

        `env`:nx.Graph

            Граф улично-дорожной сети

        `area`: pd.Series = None

            Маска узлов графа. Значениями True отмечены узлы графа - цели расчета леса Вороного.
            Если не указана, расчет производится для всех узлов графа.

        `dynamic_nodes`: dict

            Список стартовых узлов графа в которых размещены
            подразделения оптимальные места которых следует определить.

        `**kwargs`
            
            прочие аргументы определяющиеся реализацией blp_function.
        
        '''

        # Проверка входящих данных
        # Выполняется в оборачиваемой функции, поэтому здесь смысле не имеет - позже удалить
        if dynamic_nodes is None:
            raise ValueError("Аргумент `dynamic_nodes` должен быть словарем и не может быть равен None!")
        if len(dynamic_nodes) < 1:
            raise ValueError("Аргумент `dynamic_nodes` должен содержать не менее 1 узла!")
        if len(dynamic_nodes) > 1:
            warnings.warn(f"Аргумент `dynamic_nodes` содержит больше одного узла!"
                    f"Это приведет к отбрасыванию всех узлов кроме первого")

        # Получение первого узла из словаря
        start_point, start_key = list(dynamic_nodes.items())[0]

        # Расчет лучшего узла с использованием BLP
        best_node, best_metric = self.blp_function(env=env, area=area, start_point = start_point, **kwargs)

        # Конвертация результата в результат метода MCLP
        return {best_node: start_key}, best_metric