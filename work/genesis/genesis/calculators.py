'''
Различные расчетные функции.
'''

import pandas as pd
from .models import Environment



class Metrics(object):
    '''
    Функции расчета метрик.
    '''
    @staticmethod
    def calc_metric(E:Environment, 
                    node:int, 
                    path_function, 
                    metric_function, 
                    weight: str = "travel_time",
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
            Функция расчета кратчайших путей от единственного источника. 
            В качестве функции могут быть переданы реализации алгоритмов из пакета
            `networkx`. Например, реализация алгоритма Дейкстры: `nx.single_source_dijkstra_path_length`.
            Рекомендуется использовать функции указанные в `swiss_knife.ssfpl`.
            Пользователь может использовать собственные функции с
            интерфейсом `func(G: Graph, source: Any, cutoff: Any | None = None, weight: str = "weight")`

        `metric_function`: function
            Целевая функция расчета метрики. 
            В качестве функции могут быть переданы статистические функции пакета numpy,
            такие как `np.max`, `np.mean` и т.д. А т.ж. функция `Metrics.calc_ip`.
            Кроме того пользователь может использовать собственные функции с
            интерфейсом `func(route_times:pd.Series)`
        
        `weight`:str или function
            Имя поля содержащего вес ребер, или функция позволяющая вычислять 
            вес динамически.

        `precision`: int 
            Точность округления

        Возвращает
        ----------
        `metric_val`: float
            Значение целевой метрики

        Пример
        ------  
        Создание модели окружения на основе некоторого ГДС `G`:
            ```
            from genesis.calculators import Metrics
            from genesis.swiss_knife import ssfpl
            from genesis.models import Environment
            import numpy as np

            E = Environment(G)
            ```
        Расчет времени следования до наиболее удаленного узла:
            ```
            Metrics.calc_metric(E, node=1, path_function=ssfpl, metric_function=np.max)
            ```
        Расчет среднего времени прибытия в любой из узлов, с точностью до 4 знаков после'.':
            ```
            Metrics.calc_metric(E, node=1, path_function=ssfpl, metric_function=np.mean,
                precision=4)
            ```
        Расчет ИП-20, по полю 'edge_weight':
            ```
            Metrics.calc_metric(E, node=1, path_function=ssfpl, metric_function=Metrics.calc_ip(ip_val=20),
                weight='edge_weight')
            ```

        Переопределение
        ---------------
        В случаях, когда имеющегося функционала не достаточно, функция может быть заменена
        пользовательской функцией с интерфейсом:
            ```
            def I_calc_metric(E:Environment, **kwargs): float
            ```
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
    def calc_ip( 
                ip_val=10,
                precision: int = 2):
        '''
        Расчет индекса прикрытия.

        Аргументы
        ---------
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

        Пример
        ------
        Вызывается как результат выполнения функции с заданными параметрами:

        для расчета ИП-10:
            `calc_ip()` или `calc_ip(ip_val=10)`
        для расчета ИП-20:
            `calc_ip(ip_val=20)`
        для расчета ИП-10 с точностью до 4 знаков после запятой:
            `calc_ip(precision = 4)` или `calc_ip(ip_val=10, precision = 4)`
        '''
        def _calc_ip(route_times:pd.Series):
            '''Расчет индекса прикрытия.

            Аргументы
            ---------
            `route_times`:pd.Series
                Серия данных о временах прибытия в узлы ГДС 
                (или вообще произвольных данных о временах прибытия)
            '''
            if not isinstance(route_times, pd.Series):
                raise TypeError(
                    "Аргумент route_times может быть только типа pd.Series"
                    )

            tot_len = len(route_times)
            if tot_len==0:
                return 0
            ip_len = sum(route_times<=ip_val)
            return round(100*ip_len/tot_len, precision)
        return _calc_ip

    # @staticmethod
    # def calc_common():

