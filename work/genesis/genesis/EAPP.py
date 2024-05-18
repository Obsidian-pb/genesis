'''
Estimated Arrival Parameters Problem - Задача определения ожидаемых параметров реагирования пожарных подразделений

Метрики прибытия пожарных подразделений
'''

import pandas as pd
import networkx as nx
import osmnx as ox





@staticmethod
def metric(
                metric_function,
                weight: str = "arrival_time",
                err_val=None):
    '''
    Базовая функция расчета метрик времени.
    Возвращает значение указанной метрики для набора узлов.
    Может быть использована как интерфейс для разработки более специализированных функций.

    Аргументы
    ---------
    `metric_function`: function
        Целевая функция расчета метрики. 
        В качестве функции могут быть переданы статистические функции пакета numpy,
        такие как `np.max`, `np.mean` и т.д. А т.ж. функция `Metrics.calc_ip`.
        Кроме того пользователь может использовать собственные функции с
        интерфейсом `func(route_times:pd.Series)`
    
    `weight`:str или list(str) = "arrival_time"
        Имя поля содержащего вес ребер,
        или список имен полей содержащих значения для передачи `metric_function`.

    `err_val`: float
        Значение которое будет возвращено в случае ошибки


    Возвращает
    ----------
    `metric_val`: float
        Значение целевой метрики

    Пример
    ------


    Переопределение
    ---------------

    `Переписать!`

    
    '''

    def _metric(G:nx.MultiDiGraph):
        '''

        `G`: nx.MultiDiGraph=None
            Подграф. Если указан, то расчет метрики производится для него
        '''

        if not isinstance(G, nx.MultiDiGraph):
            raise TypeError("Аргумент G должен иметь тип nx.MultiDiGraph!")

        nodes = ox.graph_to_gdfs(G, edges=False, node_geometry=False)

        if isinstance(weight, list):
            if not all(w in nodes.columns for w in weight):
                raise ValueError(f'Не все указанные поля ({weight}) имеются в ' \
                                'наборе полей графа G! '\
                                'Возможно граф не рассчитан')
        elif isinstance(weight, str):
            if not weight in nodes.columns:
                raise ValueError(f'Поле {weight} отсутствует в ' \
                                'наборе полей графа G! '\
                                'Возможно граф не рассчитан')
        else:
            raise ValueError(f'Переданный тип аргумента weight ({type(weight)}) ' \
                             'не приемлем. Должен быть str или list(str)')

        try:
            val = metric_function(nodes[weight])
            return val
        except Exception as exc:
            raise TypeError(
                f"Функция {metric_function.__name__} здесь не применима. Уточните ее сигнатуру."
                ) from exc

    return _metric









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
