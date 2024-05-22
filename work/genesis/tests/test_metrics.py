'''
Тесты для расчетов метрик

`pytest tests/test_metrics.py -s`
'''

import pytest

import osmnx as ox
import networkx as nx
import numpy as np
import pandas as pd

from genesis.metrics import ArrivalTime, CoverIndex

from genesis.swiss_knife import MSF






@pytest.fixture(scope='module')
def load_G():
    return ox.load_graphml("tests/data/test_rng.ml")

# @pytest.fixture(scope='module')
# def load_area():
#     return gpd.read_file("tests/data/test_polygon.gpkg")

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
    # @pytest.mark.xfail()
    # def test_calc_max_graph_wrong_data_type(self, load_G):
    #     '''Проверка приемлемости входящих данных'''
    #     G = load_G
    #     start_node = list(G.nodes())[2000]
    #     times = nx.single_source_dijkstra_path_length(G, start_node, weight='travel_time')

    #     max_time_t = 28.881282428571428
    #     max_time = arrival_time(np.max)(times)
    #     assert max_time_t==max_time

    def test_calc_mean_time_list(self):
        '''Тест расчета среднего времени для списка'''
        l = [10,20,30,40]
        metric = ArrivalTime()(l)

        metric_est=25
        assert metric_est == metric

    def test_calc_mean_time_list_zero(self):
        '''Тест расчета среднего времени для списка нулевой длины'''
        l = []
        metric = ArrivalTime()(l)

        metric_est=0
        assert metric_est == metric

    def test_calc_max_time_list(self):
        '''Тест расчета максимального времени для списка'''
        l = [10,20,30,40]
        metric_function = ArrivalTime(f=np.max)
        metric = metric_function(l)

        metric_est=40
        assert metric_est == metric

    def test_calc_mean_time_g(self, create_G):
        '''Тест расчета среднего времени для результата расчета графа (pd.Series)'''
        G = create_G
        start_node = list(G.nodes())[0]
        times, _  = MSF(G, [start_node])
        metric = ArrivalTime()(pd.Series(times))

        metric_est=round(1.9333333333333333, 2)
        assert metric_est == round(metric, 2)






class TestIPCommon:
    '''
    Тестирование основных методов расчета индекса прикрытия
    '''
    def test_cover_index_list(self):
        '''Тест расчета ИП-10 для списка'''
        l = [1,2,3,6,10, 12,24,27,30,32]
        metric = CoverIndex()(l)

        metric_est=50.0
        assert metric_est == metric

    def test_cover_index_20_list(self):
        '''Тест расчета ИП-20 для списка'''
        l = [10,12, 24,27]
        metric_function = CoverIndex()
        metric = metric_function(l)

        metric_est=25.0
        assert metric_est == metric

    def test_cover_index_list_zero(self):
        '''Тест расчета ИП-10 для списка нулевой длины'''
        l = []
        metric = CoverIndex()(l)

        metric_est=0
        assert metric_est == metric

    def test_cover_index_g(self, create_G):
        '''Тест расчета ИП-10 для pd.Series - результата расчета графа'''
        G = create_G
        start_node = list(G.nodes())[0]
        times, _ = MSF(G, [start_node])
        metric = CoverIndex()(pd.Series(times))

        metric_est=100
        assert metric_est == int(metric)





# для узла 2000:
# {'max': 27.881282428571428,
#  'mean': 17.322393925534676,
#  'median': 17.114336285714288,
#  'ip10': 10.08357558139535,
#  'ip20': 68.75}

