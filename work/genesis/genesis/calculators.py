'''
Различные расчетные функции.
'''

import pandas as pd
from .models import Environment
from .features import RoadNetworkGraph, DislocationProfile
import networkx as nx




class Metrics(object):
    '''
    Функции расчета метрик.
    '''
    @staticmethod
    def calc_metric(E: Environment,
                    node:int,
                    path_function,
                    metric_function,
                    RNG_name: str = 'RNG',
                    weight: str = "travel_time",
                    precision: int = 2):
        '''
        Базовая функция расчета метрик.
        Возвращает значение стандартной целевой метрики.
        Может быть использована как интерфейс для разработки более специализированных функций.

        Аргументы
        ---------
        `E`:Environment (а также наследники)
            Окружение
        
        `node`:int
            Узел для которого производится расчет

        `path_function`: function
            Функция расчета кратчайших путей от единственного источника. 
            В качестве функции могут быть переданы реализации алгоритмов из пакета
            `networkx`. Например, реализация алгоритма Дейкстры: `nx.single_source_dijkstra_path_length`.
            Пользователь может использовать собственные функции с
            интерфейсом `func(G: Graph, source: Any, cutoff: Any | None = None, weight: str = "weight")`

        `metric_function`: function
            Целевая функция расчета метрики. 
            В качестве функции могут быть переданы статистические функции пакета numpy,
            такие как `np.max`, `np.mean` и т.д. А т.ж. функция `Metrics.calc_ip`.
            Кроме того пользователь может использовать собственные функции с
            интерфейсом `func(route_times:pd.Series)`

        `RNG_name`: str = 'RNG'
            Имя модели графа дорожной сети
        
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
            def I_calc_metric(E: Environment, **kwargs): float
            ```
        '''
        if not isinstance(E, Environment):
            raise TypeError("Аргумент E должен быть Окружением!")
        if not isinstance(node, int):
            raise TypeError("Идентификатор узла должен иметь тип данных int!")
        if RNG_name in E.__dict__:
            RNG = getattr(E, RNG_name)
        else:
            raise KeyError(f'{RNG_name} отсутствует в Окружении')
        if not isinstance(RNG, RoadNetworkGraph):
            raise TypeError(f"Модель {RNG_name} должна иметь тип RoadNetworkGraph!")
        if not node in RNG.nodes():
            raise KeyError(f"Узел {node} отсутствует в графе G")

        route_lens = path_function(RNG.get, node, weight=weight)

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

class Arrivals(object):
    '''
    Функции расчета времен прибытия.
    '''
    @staticmethod
    def calc_AP(E:Environment,
                path_function,
                RNG_name: str = 'RNG',
                DP_name:str = 'DP',
                DP_node_field: str = 'node',
                result_field: str = 'arrival_time',
                result_unit_field: str = 'unit',
                weight: str = 'travel_time',
                delay_time = 1.,
                cutoff=None):
        '''Расчет профиля прибытия
        
        Аргументы
        ---------
        `E`: Environment (а также наследники)
            Модель окружения
        `path_function`: function
            Функция расчета кратчайших путей от множества источника. 
            В качестве интерфейса функции выступает реализация алгоритма
            `nx.multi_source_dijkstra` из пакета `networkx`. 
            Пользователь может использовать собственные функции с
            интерфейсом `func(multi_source_dijkstra(G, sources, target=None, cutoff=None, weight='weight'))-->distance, path`
        `RNG_name`: str = 'RNG'
            Имя модели ГДС
        `DP_name`:str = 'DP'
            Имя профиля дислокации
        `DP_node_field`: str = 'node'
            Имя поля профиля дислокации в котором хранится номер узла
        `result_field`: str = 'arrival_time'
            Имя поля профиля прибытия в котором хранится время прибытия
        `result_unit_field`: str = 'unit'
            Имя поля профиля прибытия в котором хранится наименование 
            подразделения
        `weight`: str = 'travel_time'
            Имя поля ГДС в котором хранится время следования по фрагменту
            (ребру) ГДС
        `delay_time` = 1.
            Время обработки вызова - промежутка между поступлением сообщения 
            в пожарную охраны и выезда реагирующих подразделений
        `cutoff`=None
            Максимальное время следования

        Возвращает
        ----------
        `AP`: ArrivalProfile
            Профиль прибытия

        Пример использования
        --------------------

        ```
        # создание модели окружения
        E = Environment(path='tests/data/')
        E.add_features(
            [
                RoadNetworkGraph(path='test_rng.ml'),
                DislocationProfile(),
                SpeedProfile()
            ]
        ).load()
        E.crs = E['RNG'].crs

        # добавление времен следования по фрагментам ГДС
        MorphersGraph.add_edge_travel_times(E['RNG'].G, E['SP'])
        # добавление ближайших узлов для пожарных подразделений из ПД
        MorphersSpatialFeature.add_nearest_node(E['DP'], E['RNG'])

        # непосредственно расчет профиля прибытия
        df_out = Arrivals.calc_AP(E, path_function=nx.multi_source_dijkstra)
        ```

        '''
        if not isinstance(E, Environment):
            raise TypeError("Аргумент E должен быть Окружением!")
        if RNG_name in E.__dict__:
            RNG = getattr(E, RNG_name)
        else:
            raise KeyError(f'Данные ГДС с именем{RNG_name} отсутствует в Окружении')
        if DP_name in E.__dict__:
            DP = getattr(E, DP_name)
        else:
            raise KeyError(f'Данные ПД с именем{DP_name} отсутствует в Окружении')

        if not isinstance(RNG, RoadNetworkGraph):
            raise TypeError(f"Данные {RNG_name} должны иметь тип RoadNetworkGraph!")
        if not isinstance(DP, DislocationProfile):
            raise TypeError(f"Данные {DP_name} должны иметь тип DislocationProfile!")

        if not DP_node_field in DP.data.columns:
            raise KeyError(f"Поле с именем {DP_node_field} отсутствует в {DP_name}")

        # Собственно вычисления
        units_nodes = DP.data[DP_node_field].astype('int64')
        units_nodes_list = list(units_nodes)
        unit_by_node = {key: val for val, key in zip(units_nodes.index, units_nodes.astype('int64').values)}
        
        # Производим расчет времен и маршрутов:
        nodes_distances, nodes_pathes = path_function(RNG.G, sources=units_nodes_list, cutoff=cutoff, weight=weight)
        nodes_units = {nodes_pathes_key: unit_by_node[nodes_pathes_val[0]] for nodes_pathes_key, nodes_pathes_val in nodes_pathes.items()}
        
        # Оформляем итог расчета
        df_out = pd.DataFrame({result_field: nodes_distances, result_unit_field: nodes_units})
        df_out[result_field] = df_out[result_field] + delay_time

        return df_out
