'''
Реализация алгоритмов поиска оптимального размещения
заранее неизвестного количества
наилучшим образом расположенных узлов (LSCP)
'''

import networkx as nx
import pandas as pd

from .core import LSCPBase, BestPointsBase, MCLPBase, MetricBase, PointSelectorBase, StateBase, StopCaseBase
from .mclp import NodesMetric
from .tools import list_dict_concat


class LSCPCommon(LSCPBase):
    '''
    Наиболее общий модульный алгоритм расчета количества и оптимального 
    размещения узлов для достижения целевой метрики.
    '''
    def __init__(self,
                 mclp_function: MCLPBase,
                 point_selector: PointSelectorBase,
                 stop_case_function: StopCaseBase,
                 metric_function: MetricBase,
                 names_pattern: str = '{}',
                 start_names_index: int = 1,
                 after_mclp_function: callable = None,
                 **kwargs):
        self.after_mclp_function = after_mclp_function
        super().__init__(mclp_function, point_selector, stop_case_function, metric_function, names_pattern, start_names_index, **kwargs)

    def __call__(self,
                 env:nx.MultiDiGraph,
                 dynamic_nodes: dict,
                 static_nodes: dict = None,
                 area: pd.Series = None,
                 nodes_list:set=None,
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
        `nodes_list`:set=None
            Множество узлов графа которые будут рассмотрены в качестве кандидатов.
            Если не указан, то будут рассмотрены все узлы графа.
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
            # 2. Расчет текущей метрики
            if static_nodes is None:
                all_nodes = best_dynamic_nodes
            else:
                all_nodes = list_dict_concat(best_dynamic_nodes, static_nodes)
            current_metric = NodesMetric(self.mclp_function.state_function,
                                         self.metric_function
                                         )(env,
                                           list(all_nodes.keys()),
                                           area=area)
            # 3. Печать отчета расчета
            if not self.after_mclp_function is None:
                self.after_mclp_function(iteration=iteration,
                            best_metric=best_metric,
                            current_metric=current_metric,
                            dynamic_nodes=best_dynamic_nodes,
                            static_nodes=static_nodes)

            # 4. Если достигнута цель расчета, выходим из цикла
            if self.stop_case_function(value=current_metric,
                            iteration=iteration,
                            best_metric=best_metric,
                            current_metric=current_metric,
                            dynamic_nodes=best_dynamic_nodes,
                            static_nodes=static_nodes):
                return best_dynamic_nodes, current_metric

            # ============================================================================================
            # 2. Если нет - создаем новое подразделение
            # 2.1. Получение суммарного списка (или словаря) узлов для расчета состояния и метрик
            start_nodes = list_dict_concat(best_dynamic_nodes, static_nodes)

            # 2.2. Выбор нового узла в соответствии с переданной логикой
            new_node = self.point_selector(env=env, points=start_nodes, area=area)
            # print(new_node)

            # 2.3. Добавление нового узла в словарь динамических узлов:
            best_dynamic_nodes[new_node] = self.names_pattern.format(name_index)
            # print(best_dynamic_nodes)

            # ============================================================================================
            iteration += 1
            name_index += 1

        return best_dynamic_nodes, best_metric
    


def drop_trash_points(env,
                    state_function: StateBase,
                    metric_function: MetricBase,
                    stop_case_function: StopCaseBase,
                    dynamic_nodes,
                    static_nodes=None,
                    area=None,
                    ):
    '''
    Функция отброса мусорных размещений.
    В данном случае используется жадное удаление

    
    '''
    


    for node in dynamic_nodes:
        if len(dynamic_nodes) == 1:
            break
        tmp = dynamic_nodes.copy()
        tmp.pop(node)

        if static_nodes is None:
            all_nodes = tmp
        else:
            all_nodes = list_dict_concat(tmp, static_nodes)

        metric = NodesMetric(state_function, metric_function)(env, list(all_nodes.keys()), area=area)
        if stop_case_function(value=metric,
                            iteration=0,
                            best_metric=metric,
                            dynamic_nodes=tmp,
                            static_nodes=static_nodes):
            dynamic_nodes = tmp
    
    if static_nodes is None:
        all_nodes = dynamic_nodes
    else:
        all_nodes = list_dict_concat(tmp, static_nodes)
    metric = NodesMetric(state_function, metric_function)(env, list(all_nodes.keys()), area=area)
    
    return dynamic_nodes, metric