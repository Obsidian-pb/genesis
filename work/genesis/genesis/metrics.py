'''
Функции расчета метрик.
'''

import pandas as pd


# from .tools import data_frame_to_geo_data_frame

import networkx as nx
# import osmnx as ox





@staticmethod
def metric_by_time(G: nx.MultiDiGraph,
                path_function,
                metric_function,
                weight: str = "travel_time",
                appr_val=0.95,
                err_val=None):
    '''
    Базовая функция расчета метрик времени.
    Возвращает значение указанной метрики для набора узлов.
    Может быть использована как интерфейс для разработки более специализированных функций.

    Аргументы
    ---------
    `G`: nx.MultiDiGraph
        Граф дорожной сети

    `path_function`: function
        Функция расчета кратчайших путей от единственного источника. 
        В качестве функции могут быть переданы реализации алгоритмов из пакета
        `networkx`. Например, реализация алгоритма Дейкстры: `nx.multi_source_dijkstra_path_length`.
        Пользователь может использовать собственные функции с
        интерфейсом `func(G: MultiDiGraph, sources: Any, cutoff: Any | None = None, weight: str = "travel_time")`

    `metric_function`: function
        Целевая функция расчета метрики. 
        В качестве функции могут быть переданы статистические функции пакета numpy,
        такие как `np.max`, `np.mean` и т.д. А т.ж. функция `Metrics.calc_ip`.
        Кроме того пользователь может использовать собственные функции с
        интерфейсом `func(route_times:pd.Series)`
    
    `weight`:str или function  = "travel_time"
        Имя поля содержащего вес ребер, или функция позволяющая вычислять 
        вес динамически.

    `precision`: int = 2
        Точность округления

    Возвращает
    ----------
    `metric_val`: float
        Значение целевой метрики

    Пример
    ------

    `Переписать!`

    Создание модели окружения на основе некоторого ГДС `G`:
        ```
        from genesis.calculators import Metrics
        from genesis.swiss_knife import ssfpl
        from genesis.models import Environment
        import numpy as np

        E = Environment()
        RNG = RoadNetworkGraph(spatial_data=G)
        E.add_spatial_feature(RNG)
        E.load()
        ```
    Расчет времени следования до наиболее удаленного узла:
        ```
        Metrics.calc_metric(E, source=1, path_function=ssfpl, metric_function=np.max)
        ```
    Расчет среднего времени прибытия в любой из узлов, с точностью до 4 знаков после'.':
        ```
        Metrics.calc_metric(E, source=1, path_function=ssfpl, metric_function=np.mean,
            precision=4)
        ```
    Расчет ИП-20, по полю 'edge_weight':
        ```
        Metrics.calc_metric(E, source=1, path_function=ssfpl, metric_function=Metrics.calc_ip(ip_val=20),
            weight='edge_weight')
        ```

    Переопределение
    ---------------

    `Переписать!`

    В случаях, когда имеющегося функционала не достаточно, функция может быть заменена
    пользовательской функцией с интерфейсом:
        ```
        def I_calc_metric(E: Environment, **kwargs): float
        ```
    '''

    if not isinstance(G, nx.MultiDiGraph):
        raise TypeError("Аргумент G должен иметь тип nx.MultiDiGraph!")


    def _metric_by_time(sources:list|int,
                        g:nx.MultiDiGraph=None):
        '''
        
        `sources`:list(int)|int
            Узлы для которых производится расчет. Если в списке более одного узла, производится оценка метрики 
            исходя из расчета первого прибывшего подразделения. Т.е. Значение будет одно, отражающее
            состояние параметров прибытия из всех точек одновременно. Данный способ нельзя использовать для оценки 
            метрики каждого из узлов по отдельности!
        
        `g`: nx.MultiDiGraph=None
            Подграф. Если указан, то расчет метрики производится для него
        '''
        if isinstance(sources, (int, list)):
            if isinstance(sources, int):
                sources = [sources]
            if isinstance(sources, list):
                if len(sources)==0:
                    raise ValueError('В sources нет ни одного элемента!')
                for element in sources:
                    if not isinstance(element, int):
                        raise TypeError("Все идентификаторы узлов в списке sources должны иметь тип данных int!")
                    if not element in G.nodes():
                        raise KeyError(f"Узел {element} отсутствует в графе G")
        else:
            raise TypeError("Идентификатор узла должен иметь тип данных int или list(int)!")
        if not g is None:
            if not isinstance(g, nx.MultiDiGraph):
                raise TypeError("Аргумент g должен иметь тип nx.MultiDiGraph!")
        else:
            g=G

        route_lens = path_function(g, sources, weight=weight)
        if len(route_lens)<int(appr_val*g.number_of_nodes()):
            if err_val is None:
                raise ValueError(f'Метрика узла(ов) {sources} не может быть корректно вычислена в связи со слабой связностью с основным графом')
            else:
                return err_val

        try:
            val = metric_function(pd.Series(route_lens))
            return val
        except Exception as exc:
            raise TypeError(
                f"Функция {path_function.__name__} здесь не применима. Уточните ее сигнатуру."
                ) from exc

    return _metric_by_time

@staticmethod
def cover_index(
            ip_val=10):
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
    def _cover_index(route_times:pd.Series):
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
        return 100*ip_len/tot_len

    return _cover_index