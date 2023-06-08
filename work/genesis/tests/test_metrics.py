'''
Тесты для расчетов метрик

`pytest tests/test_metrics.py -s`
'''

import pytest

import osmnx as ox
import networkx as nx
import numpy as np
import pandas as pd

from genesis.models import Environment
from genesis.calculators import Metrics
from genesis.swiss_knife import ssfpl

# import logging



# lg.basicConfig(level=lg.DEBUG, filename="logs/test_metrics.log", filemode="w")


@pytest.fixture()
def load_E():
    return Environment(ox.load_graphml("tests/data/test_rng.ml"))

@pytest.fixture()
def create_E():
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
    return Environment(G)

def test_calc_max(load_E):
    E = load_E
    start_node = list(E.G.nodes())[2000]
    # lngs = nx.single_source_dijkstra_path_length(E.G, start_node, weight='length')
    # max_time_node = max(lngs, key=lngs.get)
    # max_time_t = nx.dijkstra_path_length(E.G, start_node, max_time_node, weight='length')

    max_time_t = 27.88
    max_time = Metrics.calc_metric(E,
                                   start_node,
                                   path_function=ssfpl,
                                   metric_function=np.max,
                                   weight='travel_time')
    assert max_time_t==max_time

def test_calc_mean(load_E):
    E = load_E
    start_node = list(E.G.nodes())[2000]
    # lngs = nx.single_source_dijkstra_path_length(E.G, start_node, weight='length')
    # mean_time_t = np.mean(list(lngs.values()))
    mean_time_t = 16.32
    mean_time = Metrics.calc_metric(E,
                                   start_node,
                                   path_function=ssfpl,
                                   metric_function=np.mean,
                                   weight='travel_time')
    assert mean_time_t==mean_time

def test_calc_median(load_E):
    E = load_E
    start_node = list(E.G.nodes())[2000]
    # lngs = nx.single_source_dijkstra_path_length(E.G, start_node, weight='length')
    # mean_time_t = np.median(list(lngs.values()))
    median_time_t = 17.11
    median_time = Metrics.calc_metric(E, 
                                   start_node, 
                                   path_function=ssfpl,
                                   metric_function=np.median,
                                   weight='travel_time')
    assert median_time_t==median_time

def test_calc_ip_correct_10():
    lst = [3,4,5,6,7,6,10,  12,13,14]
    ip = Metrics.calc_ip()(pd.Series(lst))
    assert 70.==ip

def test_calc_ip_correct_20():
    lst = [3,4,5,6,7,6,10,12,13,  21,25,30]
    ip = Metrics.calc_ip(ip_val=20)(pd.Series(lst))
    assert 75.==ip

def test_calc_ip_zero_len():
    ip = Metrics.calc_ip()(pd.Series())
    assert ip == 0

def test_calc_ip10(load_E):
    E = load_E
    start_node = list(E.G.nodes())[2000]
    ip_real = 11.26
    ip_test = Metrics.calc_metric(E, 
                                   start_node, 
                                   path_function=ssfpl,
                                   metric_function=Metrics.calc_ip(),
                                   weight='travel_time')
    assert ip_real==ip_test

def test_calc_ip20(load_E):
    E = load_E
    start_node = list(E.G.nodes())[2000]
    ip_real = 74.04
    ip_test = Metrics.calc_metric(E, 
                                   start_node, 
                                   path_function=ssfpl,
                                   metric_function=Metrics.calc_ip(ip_val=20),
                                   weight='travel_time')
    assert ip_real==ip_test

# для узла 2000:
# {'max': 27.881282428571428,
#  'mean': 16.322393925534676,
#  'median': 17.114336285714288,
#  'ip10': 11.26,
#  'ip20': 74.04}

def test_calc_base_overload(load_E):
    def calc_metric(E:Environment, 
                    node:int, 
                    # path_function, 
                    # metric_function, 
                    # weight: str = "travel_time",
                    # precision: int = 2,
                    **kwargs):
        route_lens = nx.single_source_dijkstra_path_length(
            E.G, node, weight='length'
            )
        less_1000 = [1 if d<1000 else 0 for d in route_lens.values()]
        return round(sum(less_1000)/len(less_1000), 2)

    E = load_E
    start_node = list(E.G.nodes())[2000]
    assert calc_metric(E, start_node)==0.05

def test_calc_simple_overload(load_E):
    def calc_ip_15(route_times:pd.Series):
        # общий размер датасета
        tot_len = len(route_times)
        # размер датасета лежащего в пределах 15 минут
        ip_15_len = sum(route_times<=15)
        # Возвращаем отношение ip_15_len к tot_len, с точностью округления 2
        return round(100*ip_15_len/tot_len, 2)

    # Применение:
    E = load_E
    start_node = list(E.G.nodes())[2000]
    metric_value = Metrics.calc_metric(E, node=start_node, path_function=ssfpl, 
        metric_function=calc_ip_15)
    assert metric_value==34.01
