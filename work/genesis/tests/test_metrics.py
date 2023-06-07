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
    ip = Metrics.calc_ip(pd.Series(lst))
    assert 70.==ip

def test_calc_ip_correct_20():
    lst = [3,4,5,6,7,6,10,12,13,  21,25,30]
    ip = Metrics.calc_ip(pd.Series(lst), ip_val=20)
    assert 75.==ip

def test_calc_ip_zero_len():
    ip = Metrics.calc_ip(pd.Series(), ip_val=20)
    assert ip == 0

def test_calc_ip10(load_E):
    E = load_E
    start_node = list(E.G.nodes())[2000]
    # lngs = nx.single_source_dijkstra_path_length(E.G, start_node, weight='length')
    # covered = [1 if t<=10 else 0 for t in lngs.values()]
    # ip_real = round(100*sum(covered)/len(covered), 2)
    ip_real = 11.26
    ip_test = Metrics.calc_metric(E, 
                                   start_node, 
                                   path_function=ssfpl,
                                   metric_function=Metrics.calc_ip,
                                   weight='travel_time')
    print(f"{ip_test}")
    assert ip_real==ip_test



# для узла 2000:
# {'max': 27.881282428571428,
#  'mean': 16.322393925534676,
#  'median': 17.114336285714288,
#  'ip10': 11.26,
#  'ip20': 74.04}