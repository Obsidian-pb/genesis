'''
Тесты для расчетов метрик

`pytest tests/test_metrics.py -s`
'''

import pytest

import osmnx as ox
import networkx as nx
import numpy as np
import pandas as pd


from genesis.EAPP import *
from genesis.swiss_knife import msfpl

# import logging



# lg.basicConfig(level=lg.DEBUG, filename="logs/test_metrics.log", filemode="w")


@pytest.fixture(scope='module')
def load_G():
    return ox.load_graphml("tests/data/test_rng.ml")

@pytest.fixture(scope='module')
def create_G():
    '''
        max: 21
        mean: 8.67
        median: 8.0
        ip-10: 66.67
        ip-20: 93.33
    '''
    G = nx.MultiDiGraph()
    G.add_edge(1, 2, key=0, travel_time=3)
    G.add_edge(1, 3, key=0, travel_time=2)
    G.add_edge(1, 4, key=0, travel_time=5)
    G.add_edge(2, 3, key=0, travel_time=2)
    G.add_edge(2, 5, key=0, travel_time=5)
    G.add_edge(2, 6, key=0, travel_time=7)
    G.add_edge(3, 2, key=0, travel_time=3)
    G.add_edge(3, 7, key=0, travel_time=3)
    G.add_edge(3, 8, key=0, travel_time=4)
    G.add_edge(3, 9, key=0, travel_time=5)
    G.add_edge(4, 3, key=0, travel_time=2)
    G.add_edge(4, 8, key=0, travel_time=4)
    G.add_edge(4, 10, key=0, travel_time=12)
    G.add_edge(4, 11, key=0, travel_time=10)
    G.add_edge(5, 8, key=0, travel_time=8)
    G.add_edge(5, 10, key=0, travel_time=8)
    G.add_edge(5, 12, key=0, travel_time=6)
    G.add_edge(5, 13, key=0, travel_time=9)
    G.add_edge(5, 12, key=0, travel_time=8)
    G.add_edge(6, 8, key=0, travel_time=1)
    G.add_edge(6, 9, key=0, travel_time=4)
    G.add_edge(6, 12, key=0, travel_time=4)
    G.add_edge(7, 10, key=0, travel_time=4)
    G.add_edge(7, 11, key=0, travel_time=9)
    G.add_edge(7, 13, key=0, travel_time=7)
    G.add_edge(8, 10, key=0, travel_time=6)
    G.add_edge(8, 13, key=0, travel_time=8)
    G.add_edge(9, 14, key=0, travel_time=10)
    G.add_edge(10, 13, key=0, travel_time=7)
    G.add_edge(10, 14, key=0, travel_time=5)
    G.add_edge(11, 12, key=0, travel_time=7)
    G.add_edge(11, 15, key=0, travel_time=7)
    G.add_edge(12, 13, key=0, travel_time=8)
    return G


class TestMetricsG:
    '''
    Тестирование расчета метрик при передаче аргументом ГДС
    '''
    def test_calc_max_single_node(self, load_G):
        '''Тест расчета метрики максимального времени следования из одного узла'''
        G = load_G
        start_node = list(G.nodes())[2000]
        routes = nx.single_source_dijkstra_path_length(G, start_node, weight='travel_time')
        nx.set_node_attributes(G, routes, 'arrival_time')

        max_time_t = 27.881282428571428
        max_time = metric(metric_function=np.max)(G)
        assert max_time_t==max_time

    def test_calc_mean_single_node(self, load_G):
        '''Тест расчета метрики среднего времени следования из одного узла'''
        G = load_G
        start_node = list(G.nodes())[2000]
        routes = nx.single_source_dijkstra_path_length(G, start_node, weight='travel_time')
        nx.set_node_attributes(G, routes, 'arrival_time')

        mean_time_t = 16.322393925534676
        mean_time = metric(metric_function=np.mean)(G)
        assert mean_time_t==mean_time


    def test_calc_custom_single_node(self, load_G):
        '''
            Тест расчета пользовательской метрики для одного узла
            В качестве примера взята метрика ИП-10
        '''

        def custom_metric_function(s:pd.Series):
            return len(s[s<=10])/len(s)

        G = load_G
        start_node = list(G.nodes())[500]
        routes = nx.single_source_dijkstra_path_length(G, start_node, weight='travel_time')
        nx.set_node_attributes(G, routes, 'arrival_time')

        val_t = 0.7136380123322452
        val = metric(metric_function=custom_metric_function)(G)
        assert val_t==val


    def test_calc_custom_single_node_2_columns(self, load_G):
        '''
            Тест расчета пользовательской метрики для одного узла
            и двух колонок
        '''

        def custom_metric_function_2_columns(df:pd.DataFrame):
            return np.max(df['x']+df['y'])

        G = load_G    

        val_t = 149.5709272
        val = metric(metric_function=custom_metric_function_2_columns,
                    weight=['x', 'y'])(G)
        assert val_t==val


    def test_calc_max_multi_node(self, load_G):
        '''Тест расчета метрики максимального времени следования из нескольких узлов'''
        G = load_G
        start_nodes = [list(G.nodes())[1000], list(G.nodes())[2000]]
        routes = nx.multi_source_dijkstra_path_length(G, start_nodes, weight='travel_time')
        nx.set_node_attributes(G, routes, 'arrival_time')

        max_time_t = 18.329245285714283
        max_time = metric(metric_function=np.max)(G)
        assert max_time_t==max_time


    def test_calc_max_multi_node_reverse(self, load_G):
        '''
        Расчет для случая когда нужно определить время прибытия не ИЗ точек, а В них
        '''
        def shortest_path_length_r(G, target, weight):
            Gr = nx.reverse(G)
            return nx.multi_source_dijkstra_path_length(Gr, sources=target, weight=weight)

        G = load_G
        start_nodes = [list(G.nodes())[1000], list(G.nodes())[2000]]
        routes = shortest_path_length_r(G, start_nodes, weight='travel_time')
        nx.set_node_attributes(G, routes, 'arrival_time')

        max_time_t = 19.199067214285723
        max_time = metric(metric_function=np.max)(G)
        assert max_time_t==max_time


    def test_calc_mean_single_node_column_rename(self, load_G):
        '''
        Тест расчета метрики среднего времени следования из одного узла.
        Переопределяется имя поля данных.
        '''
        # weight_field = 'time_of_arrival' # Для наглядности переменная не используется, но в реальных программах лучше использовать
        G = load_G
        start_node = list(G.nodes())[2000]
        routes = nx.single_source_dijkstra_path_length(G, start_node, weight='travel_time')
        nx.set_node_attributes(G, routes, 'time_of_arrival')

        mean_time_t = 16.322393925534676
        mean_time = metric(metric_function=np.mean,
                            weight='time_of_arrival')(G)
        assert mean_time_t==mean_time


    @pytest.mark.xfail()
    def test_calc_mean_single_node_wrong_weight(self, load_G):
        '''
        Расчет для подграфа и одного узла.
        Передано не верное имя поля - ОШИБКА
        '''
        G = load_G
        start_node = list(G.nodes())[100]
        routes = nx.single_source_dijkstra_path_length(G, start_node, weight='travel_time')
        nx.set_node_attributes(G, routes, 'arrival_time')

        mean_time_t = 1
        mean_time = metric(metric_function=np.mean, weight='another_column')(G)
        assert mean_time_t==mean_time


    def test_cover_index_10(self, load_G):
        '''Тест расчета ИП для 10 минутной зоны '''
        G = load_G
        start_node = list(G.nodes())[500]
        routes = nx.single_source_dijkstra_path_length(G, start_node, weight='travel_time')
        nx.set_node_attributes(G, routes, 'arrival_time')

        mean_time_t = 71.36380123322452
        mean_time = metric(metric_function=cover_index())(G)
        assert mean_time_t==mean_time


    def test_cover_index_20(self, load_G):
        '''Тест расчета ИП для 20 минутной зоны '''
        G = load_G
        start_node = list(G.nodes())[500]
        routes = nx.single_source_dijkstra_path_length(G, start_node, weight='travel_time')
        nx.set_node_attributes(G, routes, 'arrival_time')

        mean_time_t = 99.32898077620602
        mean_time = metric(metric_function=cover_index(20))(G)
        assert mean_time_t==mean_time


    def test_cover_index_10_multi_nodes(self, load_G):
        '''
            Тест расчета ИП для 10 минутной зоны.
            Для нескольких узлов
        '''
        G = load_G
        start_nodes = [list(G.nodes())[500], list(G.nodes())[1500]]
        routes = nx.multi_source_dijkstra_path_length(G, start_nodes, weight='travel_time')
        nx.set_node_attributes(G, routes, 'arrival_time')

        mean_time_t = 84.74791439970983
        mean_time = metric(metric_function=cover_index())(G)
        assert mean_time_t==mean_time






    def test_calc_mean_single_node_subgraph(self, load_G):
        '''
        Расчет для подграфа и одного узла
        '''
        G = load_G
        start_node = list(G.nodes())[100]
        routes = nx.single_source_dijkstra_path_length(G, start_node, weight='travel_time')
        nx.set_node_attributes(G, routes, 'arrival_time')
        nodes = ox.graph_to_gdfs(G, edges=False)
        arrived_nodes = nodes.query('arrival_time<=2')
        g = G.subgraph(arrived_nodes.index)

        mean_time_t = 1.3907426034031414
        mean_time = metric(metric_function=np.mean)(g)
        assert mean_time_t==mean_time

    @pytest.mark.xfail()
    def test_calc_mean_single_node_subgraph_wrong_type_g(self, load_G):
        '''
        Расчет для подграфа и одного узла.
        Передан не верный тип подграфа - ОШИБКА
        '''
        G = load_G
        start_node = list(G.nodes())[100]
        routes = nx.single_source_dijkstra_path_length(G, start_node, weight='travel_time')
        nx.set_node_attributes(G, routes, 'arrival_time')
        nodes = ox.graph_to_gdfs(G, edges=False)
        arrived_nodes = nodes.query('arrival_time<=2')
        g = nx.MultiGraph(G.subgraph(arrived_nodes.index))

        mean_time_t = 1.3907426034031414
        mean_time = metric(metric_function=np.mean)(g)
        assert mean_time_t==mean_time


class TestMetricsDF:
    '''
    Тестирование расчета метрик при передаче аргументом набора данных
    DataFrame или GeoDataFrame
    '''
    def test_calc_max_single_node(self, load_G):
        '''Тест расчета метрики максимального времени следования из одного узла'''
        G = load_G
        start_node = list(G.nodes())[2000]
        routes = nx.single_source_dijkstra_path_length(G, start_node, weight='travel_time')
        nx.set_node_attributes(G, routes, 'arrival_time')

        max_time_t = 27.881282428571428
        max_time = metric(metric_function=np.max)(ox.graph_to_gdfs(G, edges=False, node_geometry=False))
        assert max_time_t==max_time

    def test_calc_mean_single_node(self, load_G):
        '''Тест расчета метрики среднего времени следования из одного узла'''
        G = load_G
        start_node = list(G.nodes())[2000]
        routes = nx.single_source_dijkstra_path_length(G, start_node, weight='travel_time')
        nx.set_node_attributes(G, routes, 'arrival_time')

        mean_time_t = 16.322393925534676
        mean_time = metric(metric_function=np.mean)(ox.graph_to_gdfs(G, edges=False, node_geometry=False))
        assert mean_time_t==mean_time


    def test_calc_custom_single_node(self, load_G):
        '''
            Тест расчета пользовательской метрики для одного узла
            В качестве примера взята метрика ИП-10
        '''

        def custom_metric_function(s:pd.Series):
            return len(s[s<=10])/len(s)

        G = load_G
        start_node = list(G.nodes())[500]
        routes = nx.single_source_dijkstra_path_length(G, start_node, weight='travel_time')
        nx.set_node_attributes(G, routes, 'arrival_time')

        val_t = 0.7136380123322452
        val = metric(metric_function=custom_metric_function)(ox.graph_to_gdfs(G, edges=False, node_geometry=False))
        assert val_t==val


    def test_calc_custom_single_node_2_columns(self, load_G):
        '''
            Тест расчета пользовательской метрики для одного узла
            и двух колонок
        '''

        def custom_metric_function_2_columns(df:pd.DataFrame):
            return np.max(df['x']+df['y'])

        G = load_G    

        val_t = 149.5709272
        val = metric(metric_function=custom_metric_function_2_columns,
                    weight=['x', 'y'])(ox.graph_to_gdfs(G, edges=False, node_geometry=False))
        assert val_t==val


    def test_calc_max_multi_node(self, load_G):
        '''Тест расчета метрики максимального времени следования из нескольких узлов'''
        G = load_G
        start_nodes = [list(G.nodes())[1000], list(G.nodes())[2000]]
        routes = nx.multi_source_dijkstra_path_length(G, start_nodes, weight='travel_time')
        nx.set_node_attributes(G, routes, 'arrival_time')

        max_time_t = 18.329245285714283
        max_time = metric(metric_function=np.max)(ox.graph_to_gdfs(G, edges=False, node_geometry=False))
        assert max_time_t==max_time


    def test_calc_max_multi_node_reverse(self, load_G):
        '''
        Расчет для случая когда нужно определить время прибытия не ИЗ точек, а В них
        '''
        def shortest_path_length_r(G, target, weight):
            Gr = nx.reverse(G)
            return nx.multi_source_dijkstra_path_length(Gr, sources=target, weight=weight)

        G = load_G
        start_nodes = [list(G.nodes())[1000], list(G.nodes())[2000]]
        routes = shortest_path_length_r(G, start_nodes, weight='travel_time')
        nx.set_node_attributes(G, routes, 'arrival_time')

        max_time_t = 19.199067214285723
        max_time = metric(metric_function=np.max)(ox.graph_to_gdfs(G, edges=False, node_geometry=False))
        assert max_time_t==max_time


    def test_calc_mean_single_node_column_rename(self, load_G):
        '''
        Тест расчета метрики среднего времени следования из одного узла.
        Переопределяется имя поля данных.
        '''
        # weight_field = 'time_of_arrival' # Для наглядности переменная не используется, но в реальных программах лучше использовать
        G = load_G
        start_node = list(G.nodes())[2000]
        routes = nx.single_source_dijkstra_path_length(G, start_node, weight='travel_time')
        nx.set_node_attributes(G, routes, 'time_of_arrival')

        mean_time_t = 16.322393925534676
        mean_time = metric(metric_function=np.mean,
                            weight='time_of_arrival')(ox.graph_to_gdfs(G, edges=False, node_geometry=False))
        assert mean_time_t==mean_time


    @pytest.mark.xfail()
    def test_calc_mean_single_node_wrong_weight(self, load_G):
        '''
        Расчет для подграфа и одного узла.
        Передано не верное имя поля - ОШИБКА
        '''
        G = load_G
        start_node = list(G.nodes())[100]
        routes = nx.single_source_dijkstra_path_length(G, start_node, weight='travel_time')
        nx.set_node_attributes(G, routes, 'arrival_time')

        mean_time_t = 1
        mean_time = metric(metric_function=np.mean, weight='another_column')(ox.graph_to_gdfs(G, edges=False, node_geometry=False))
        assert mean_time_t==mean_time


    def test_cover_index_10(self, load_G):
        '''Тест расчета ИП для 10 минутной зоны '''
        G = load_G
        start_node = list(G.nodes())[500]
        routes = nx.single_source_dijkstra_path_length(G, start_node, weight='travel_time')
        nx.set_node_attributes(G, routes, 'arrival_time')

        mean_time_t = 71.36380123322452
        mean_time = metric(metric_function=cover_index())(ox.graph_to_gdfs(G, edges=False, node_geometry=False))
        assert mean_time_t==mean_time


    def test_cover_index_20(self, load_G):
        '''Тест расчета ИП для 20 минутной зоны '''
        G = load_G
        start_node = list(G.nodes())[500]
        routes = nx.single_source_dijkstra_path_length(G, start_node, weight='travel_time')
        nx.set_node_attributes(G, routes, 'arrival_time')

        mean_time_t = 99.32898077620602
        mean_time = metric(metric_function=cover_index(20))(ox.graph_to_gdfs(G, edges=False, node_geometry=False))
        assert mean_time_t==mean_time


    def test_cover_index_10_multi_nodes(self, load_G):
        '''
            Тест расчета ИП для 10 минутной зоны.
            Для нескольких узлов
        '''
        G = load_G
        start_nodes = [list(G.nodes())[500], list(G.nodes())[1500]]
        routes = nx.multi_source_dijkstra_path_length(G, start_nodes, weight='travel_time')
        nx.set_node_attributes(G, routes, 'arrival_time')

        mean_time_t = 84.74791439970983
        mean_time = metric(metric_function=cover_index())(ox.graph_to_gdfs(G, edges=False, node_geometry=False))
        assert mean_time_t==mean_time






    def test_calc_mean_single_node_subgraph(self, load_G):
        '''
        Расчет для подграфа и одного узла
        '''
        G = load_G
        start_node = list(G.nodes())[100]
        routes = nx.single_source_dijkstra_path_length(G, start_node, weight='travel_time')
        nx.set_node_attributes(G, routes, 'arrival_time')
        nodes = ox.graph_to_gdfs(G, edges=False)
        arrived_nodes = nodes.query('arrival_time<=2')
        g = G.subgraph(arrived_nodes.index)

        mean_time_t = 1.3907426034031414
        mean_time = metric(metric_function=np.mean)(g)
        assert mean_time_t==mean_time

    @pytest.mark.xfail()
    def test_calc_mean_single_node_subgraph_wrong_type_g(self, load_G):
        '''
        Расчет для подграфа и одного узла.
        Передан не верный тип подграфа - ОШИБКА
        '''
        G = load_G
        start_node = list(G.nodes())[100]
        routes = nx.single_source_dijkstra_path_length(G, start_node, weight='travel_time')
        nx.set_node_attributes(G, routes, 'arrival_time')
        nodes = ox.graph_to_gdfs(G, edges=False)
        arrived_nodes = nodes.query('arrival_time<=2')
        g = nx.MultiGraph(G.subgraph(arrived_nodes.index))

        mean_time_t = 1.3907426034031414
        mean_time = metric(metric_function=np.mean)(g)
        assert mean_time_t==mean_time





class TestIPCommon:
    '''
    Тестирование основных методов расчета индекса прикрытия
    '''
    @pytest.mark.xfail()
    def test_cover_index_wrong_argument_type(self):
        '''Тест передачи на вход некорректного формата данных'''
        lst = [3,4,5,6,7,6,10,  12,13,14]
        ip = cover_index()(lst)
        assert 70.==ip

    def test_cover_index_correct_10(self):
        lst = [3,4,5,6,7,6,10,  12,13,14]
        ip = cover_index()(pd.Series(lst))
        assert 70.==ip

    def test_cover_index_correct_20(self):
        lst = [3,4,5,6,7,6,10,12,13,  21,25,30]
        ip = cover_index(ip_val=20)(pd.Series(lst))
        assert 75.==ip

    def test_cover_index_zero_len(self):
        '''Тест передачи функции расчета ИП данных нулевой длинны'''
        ip = cover_index()(pd.Series())
        assert ip == 0


# для узла 2000:
# {'max': 27.881282428571428,
#  'mean': 16.322393925534676,
#  'median': 17.114336285714288,
#  'ip10': 11.26,
#  'ip20': 74.04}



# def test_calc_base_overload(load_G):
#     def calc_node_metric(G:nx.MultiDiGraph, 
#                     source:int, 
#                     # path_function, 
#                     # metric_function, 
#                     # weight: str = "travel_time",
#                     # precision: int = 2,
#                     **kwargs):
#         '''
#         Для одного узла вместо списка
#         '''
#         route_lens = nx.single_source_dijkstra_path_length(
#             G, source, weight='length'
#             )
#         less_1000 = [1 if d<1000 else 0 for d in route_lens.values()]
#         return round(sum(less_1000)/len(less_1000), 2)

#     G = load_G
#     start_node = list(G.nodes())[2000]
#     assert calc_node_metric(G, start_node)==0.05

# def test_calc_simple_overload(load_G):
#     def calc_ip_15(route_times:pd.Series):
#         # общий размер датасета
#         tot_len = len(route_times)
#         # сумма датасета лежащего в пределах 15 минут
#         ip_15_sum = sum(route_times<=15)
#         # Возвращаем отношение ip_15_len к tot_len, с точностью округления 2
#         return round(100*ip_15_sum/tot_len, 2)

#     # Применение:
#     G = load_G
#     start_node = list(G.nodes())[2000]

#     metric_value = metric_by_time(G,
#                                     path_function=msfpl,
#                                     metric_function=calc_ip_15)(start_node)
    
#     assert metric_value==34.01
