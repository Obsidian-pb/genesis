'''
Тесты для расчетов метрик

`pytest tests/test_metrics.py -s`
'''

import pytest

import osmnx as ox
import networkx as nx
import numpy as np
import pandas as pd


from genesis.estimated_arrival_parameters import *
from genesis.optimal_service_areas import voronoi_forest, voronoi_forest_for_points, voronoi_forest_for_area
from genesis.swiss_knife import MSF

# import logging



# lg.basicConfig(level=lg.DEBUG, filename="logs/test_metrics.log", filemode="w")


@pytest.fixture(scope='module')
def load_G():
    return ox.load_graphml("tests/data/test_rng.ml")

@pytest.fixture(scope='module')
def load_area():
    return gpd.read_file("tests/data/test_polygon.gpkg")

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




class TestMetricsArrivalTime:
    '''
    Тестирование расчета метрики времени прибытия
    '''
    @pytest.mark.xfail()
    def test_calc_max_graph_wrong_data_type(self, load_G):
        '''Проверка приемлемости входящих данных'''
        G = load_G
        start_node = list(G.nodes())[2000]
        times = nx.single_source_dijkstra_path_length(G, start_node, weight='travel_time')

        max_time_t = 28.881282428571428
        max_time = arrival_time(np.max)(times)
        assert max_time_t==max_time

    def test_calc_max_graph(self, load_G):
        '''Тест расчета метрики максимального времени следования из одного узла'''
        G = load_G
        start_node = list(G.nodes())[2000]
        times = nx.single_source_dijkstra_path_length(G, start_node, weight='travel_time')

        time_t = 28.881282428571428
        time = arrival_time(np.max)(pd.Series(times))
        assert time_t==time

    def test_calc_mean_graph(self, load_G):
        '''Тест расчета метрики среднего времени следования из одного узла'''
        G = load_G
        start_node = list(G.nodes())[3000]
        times = nx.single_source_dijkstra_path_length(G, start_node, weight='travel_time')

        time_t = 11.595102796316963
        time = arrival_time(np.mean)(pd.Series(times))
        assert time_t==time

    def test_calc_mean_graph_multi_nodes(self, load_G):
        '''Тест расчета метрики среднего времени следования из нескольких узлов'''
        G = load_G
        start_nodes = [list(G.nodes())[1000], list(G.nodes())[3000]]
        times = nx.multi_source_dijkstra_path_length(G, start_nodes, weight='travel_time')

        time_t = 7.27785097308451
        time = arrival_time(np.mean)(pd.Series(times))
        assert time_t==time

    def test_arr_time_zero_len(self):
        '''Тест передачи функции расчета времени прибытия данных нулевой длинны'''
        ip = arrival_time(np.mean)(pd.Series())
        assert ip == 0

    def test_arr_time_custom_function(self, load_G):
        '''Тест расчета метрики времени прибытия для кастомной функции'''
        def custom(route_times: pd.Series):
            '''Возвращается значение первого квартиля'''
            route_times.sort_values(inplace=True, ascending=True)
            return np.max(route_times[:int(len(route_times)*0.25)])

        G = load_G
        start_node = list(G.nodes())[3000]
        times = nx.single_source_dijkstra_path_length(G, start_node, weight='travel_time')

        time_t = 5.543804571428573
        time = custom(pd.Series(times))
        assert time_t==time









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

    def test_cover_index_correct_10_graph(self, load_G):
        '''Тест расчета ИП-10 для реального графа'''
        G = load_G
        start_node = list(G.nodes())[2000]
        times = nx.single_source_dijkstra_path_length(G, start_node, weight='travel_time')

        ip = cover_index()(pd.Series(times))
        assert 10.08357558139535==ip

    def test_cover_index_correct_20_graph(self, load_G):
        '''Тест расчета ИП-20 для реального графа'''
        G = load_G
        start_node = list(G.nodes())[2000]
        times = nx.single_source_dijkstra_path_length(G, start_node, weight='travel_time')

        ip = cover_index(20)(pd.Series(times))
        assert 68.75==ip



class TestMetricsForNode:
    '''Тесты расчета метрик для единичного узла'''
    def test_single_node_metric_real_graph(self, load_G):
        '''Расчет метрики для одного узла'''
        G = load_G
        start_node = [list(G.nodes())[2000]]

        val = nodes_metric(G=G, sources=start_node, 
            path_function=MSF,
            metric_function=arrival_time(np.mean),
            voronoi_function=voronoi_forest)
        val_t = 17.322393925534676
        assert val_t == val

    def test_multi_node_metric_real_graph(self, load_G):
        '''Расчет метрики для множества узла'''
        G = load_G
        start_nodes = [list(G.nodes())[2000], list(G.nodes())[4000]]

        val = nodes_metric(G=G, sources=start_nodes, 
            path_function=MSF,
            metric_function=arrival_time(np.mean),
            voronoi_function=voronoi_forest)
        val_t = 10.098875894894622
        assert val_t == val

    def test_multi_node_metric_real_graph_area(self, load_G, load_area):
        '''Расчет метрики для множества узлов и ограничения полигоном'''
        G = load_G
        area = load_area
        start_nodes = [list(G.nodes())[2000], list(G.nodes())[4000]]

        val = nodes_metric(G=G, sources=start_nodes, 
            path_function=MSF,
            metric_function=arrival_time(np.mean),
            voronoi_function=voronoi_forest_for_area,
            area=area)
        val_t = 9.404841331151413
        assert val_t == val






# для узла 2000:
# {'max': 27.881282428571428,
#  'mean': 17.322393925534676,
#  'median': 17.114336285714288,
#  'ip10': 10.08357558139535,
#  'ip20': 68.75}

