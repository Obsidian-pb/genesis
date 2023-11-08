'''
Тесты для расчетов метрик

`pytest tests/test_metrics.py -s`
'''

import pytest

import osmnx as ox
import networkx as nx
import numpy as np
import pandas as pd


from genesis.metrics import *
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

def test_calc_max_single_node(load_G):
    G = load_G
    start_node = list(G.nodes())[2000]

    max_time_t = 27.881282428571428
    max_time = calc_node_metric(G,
                            path_function=msfpl,
                            metric_function=np.max,
                            weight='travel_time')(start_node)
    assert max_time_t==max_time

def test_calc_max_multi_node(load_G):
    G = load_G
    start_nodes = [list(G.nodes())[1000], list(G.nodes())[2000]]

    max_time_t = 18.329245285714283
    max_time = calc_node_metric(G,
                            path_function=msfpl,
                            metric_function=np.max,
                            weight='travel_time')(start_nodes)
    assert max_time_t==max_time

def test_calc_max_multi_node_reverse(load_G):
    '''
    Расчет для случая когда нужно определить время прибытия не ИЗ точек, а В них
    '''
    def shortest_path_length_r(G, target, weight):
        Gr = nx.reverse(G)
        return nx.multi_source_dijkstra_path_length(Gr, sources=target, weight=weight)
    
    G = load_G
    start_nodes = [list(G.nodes())[1000], list(G.nodes())[2000]]

    max_time_t = 19.199067214285723
    max_time = calc_node_metric(G,
                            path_function=shortest_path_length_r,
                            metric_function=np.max,
                            weight='travel_time')(start_nodes)
    assert max_time_t==max_time

def test_calc_mean(load_G):
    G = load_G
    start_node = list(G.nodes())[2000]

    mean_time_t = 16.322393925534676
    mean_time = calc_node_metric(G,
                            path_function=msfpl,
                            metric_function=np.mean,
                            weight='travel_time')(start_node)
    assert mean_time_t==mean_time

def test_calc_median(load_G):
    G = load_G
    start_node = list(G.nodes())[2000]

    median_time_t = 17.114336285714288
    median_time = calc_node_metric(G,
                            path_function=msfpl,
                            metric_function=np.median,
                            weight='travel_time')(start_node)
    assert median_time_t==median_time

@pytest.mark.xfail()
def test_cover_index_wrong_argument_type():
    '''Тест передачи на вход некорректного формата данных'''
    lst = [3,4,5,6,7,6,10,  12,13,14]
    ip = cover_index()(lst)
    assert 70.==ip

def test_cover_index_correct_10():
    lst = [3,4,5,6,7,6,10,  12,13,14]
    ip = cover_index()(pd.Series(lst))
    assert 70.==ip

def test_cover_index_correct_20():
    lst = [3,4,5,6,7,6,10,12,13,  21,25,30]
    ip = cover_index(ip_val=20)(pd.Series(lst))
    assert 75.==ip

def test_cover_index_zero_len():
    ip = cover_index()(pd.Series())
    assert ip == 0

def test_cover_index10(load_G):
    G = load_G
    start_node = list(G.nodes())[2000]
    ip_real = 11.26453488372093
    ip_test = calc_node_metric(G,
                            path_function=msfpl,
                            metric_function=cover_index(),
                            weight='travel_time')(start_node)
    assert ip_real==ip_test

def test_calc_ip20(load_G):
    G = load_G
    start_node = list(G.nodes())[2000]
    ip_real = 74.03706395348837
    ip_test = calc_node_metric(G,
                            path_function=msfpl,
                            metric_function=cover_index(ip_val=20),
                            weight='travel_time')(start_node)
    assert ip_real==ip_test

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

def test_calc_simple_overload(load_G):
    def calc_ip_15(route_times:pd.Series):
        # общий размер датасета
        tot_len = len(route_times)
        # сумма датасета лежащего в пределах 15 минут
        ip_15_sum = sum(route_times<=15)
        # Возвращаем отношение ip_15_len к tot_len, с точностью округления 2
        return round(100*ip_15_sum/tot_len, 2)

    # Применение:
    G = load_G
    start_node = list(G.nodes())[2000]

    metric_value = calc_node_metric(G,
                                    path_function=msfpl,
                                    metric_function=calc_ip_15)(start_node)
    
    assert metric_value==34.01
