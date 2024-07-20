'''
Реализация алгоритмов поиска оптимального размещения
заранее неизвестного количества
наилучшим образом расположенных узлов (LSCP)
'''

import networkx as nx
import pandas as pd

from genesis.core import LSCPBase, BestPointsBase, PointSelectorBase, StopCaseBase
from genesis.tools import list_dict_concat


class LSCPCommon(LSCPBase):
    '''
    Наиболее общий модульный алгоритм расчета количества и оптимального 
    размещения узлов для достижения целевой метрики.
    '''
    def __init__(self,
                 mclp_function: BestPointsBase,
                 point_selector: PointSelectorBase,
                 stop_case_function: StopCaseBase,
                 names_pattern: str = '{}',
                 start_names_index: int = 1,
                 after_mclp_function: callable = None,
                 **kwargs):
        self.after_mclp_function = after_mclp_function
        super().__init__(mclp_function, point_selector, stop_case_function, names_pattern, start_names_index, **kwargs)

    def __call__(self,
                 env:nx.MultiDiGraph,
                 dynamic_nodes: dict,
                 static_nodes: dict = None,
                 area: pd.Series = None,
                 **kwargs):
        '''
        Запуск работы алгоритма

        ## Аргументы
        `env`:nx.MultiDiGraph
            Граф улично-дорожной сети
        `dynamic_nodes`: list|dict
            Список стартовых узлов графа в которых размещены
            подразделения оптимальные места которых следует определить.
        `static_nodes`: list|dict = None
            Список стартовых узлов графа в которых размещены
            подразделения изменять размещение которых не следует.
        `area`: pd.Series = None
            Маска узлов графа. Значениями True отмечены узлы графа - цели расчета леса Вороного.
            Если не указана, расчет производится для всех узлов графа.
        '''

        # 0. Проверка корректности пришедших данных
        if not isinstance(env, nx.MultiDiGraph):
            raise TypeError("Тип аргумента `env` должен быть MultiDiGraph!")
        if not static_nodes is None:
            if not (isinstance(dynamic_nodes,dict) and isinstance(static_nodes,dict)):
                raise TypeError(f'Аргументы `dynamic_nodes` и `static_nodes` должны быть одинакового типа: dict'
                                f'Имеют: {type(dynamic_nodes)}, {type(static_nodes)}')
        if not area is None and not isinstance(area, pd.Series):
            raise TypeError(f'Аргумент `area` должен иметь тип `pd.Series`! Имеет {type(area)}')
      
        # 0.1. Если статические узлы не указаны - заменяем значение переменной с None на {}
        if static_nodes is None:
            static_nodes = {}
        if len(static_nodes) + len(dynamic_nodes) == 0:
            raise ValueError('Суммарное количество элементов `static_nodes` и `dynamic_nodes` не может быть равно 0! ' + \
                            'В случае если в `env` отсутствуют известные размещения `points`, ' + \
                            'используйте методы класса `BestPointsBase`')

        # Итерации
        best_dynamic_nodes = dynamic_nodes
        iteration = 0
        name_index = self.start_names_index
        while True:
            # 1. Расчет оптимального размещения подразделений
            best_dynamic_nodes, best_metric = self.mclp_function(env=env,
                                            dynamic_nodes=best_dynamic_nodes,
                                            static_nodes=static_nodes,
                                            area=area,
                                            **kwargs)
            if not self.after_mclp_function is None:
                self.after_mclp_function(iteration=iteration,
                            best_metric=best_metric,
                            dynamic_nodes=best_dynamic_nodes,
                            static_nodes=static_nodes)

            # 2. Если достигнута цель расчета, выходим из цикла
            if self.stop_case_function(value=best_metric,
                            iteration=iteration,
                            best_metric=best_metric,
                            dynamic_nodes=best_dynamic_nodes,
                            static_nodes=static_nodes):
                return best_dynamic_nodes, best_metric

            # ============================================================================================
            # 2. Если нет - создаем новое подразделение
            # 2.1. Получение суммарного списка (или словаря) узлов для расчета состояния и метрик
            start_nodes = list_dict_concat(dynamic_nodes, static_nodes)

            # 2.2. Выбор нового узла в соответствии с переданной логикой
            new_node = self.point_selector(env, start_nodes)

            # 2.3. Добавление нового узла в словарь динамических узлов:
            best_dynamic_nodes[new_node] = self.names_pattern.format(name_index)

            # ============================================================================================
            iteration += 1
            name_index += 1

        return best_dynamic_nodes, best_metric