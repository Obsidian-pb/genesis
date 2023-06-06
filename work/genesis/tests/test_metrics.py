import pytest

import osmnx as ox
import networkx as nx
import numpy as np
import pandas as pd

from genesis.models import Environment
from genesis.calcalators import Metrics


@pytest.fixture()
def load_E():
    return Environment(ox.load_graphml("tests/data/test_rng.ml"))

def test_calc_max(load_E):
    E = load_E
    start_node = list(E.G.nodes())[100]
    lngs = nx.single_source_dijkstra_path_length(E.G, start_node, weight='length')
    max_time_node = max(lngs, key=lngs.get)
    max_time_t = nx.dijkstra_path_length(E.G, start_node, max_time_node, weight='length')

    max_time = Metrics.metric_calc(E, start_node, weight='length')
    assert max_time_t==max_time

def test_calc_mean(load_E):
    E = load_E
    start_node = list(E.G.nodes())[100]
    lngs = nx.single_source_dijkstra_path_length(E.G, start_node, weight='length')
    mean_time_t = np.mean(list(lngs.values()))

    mean_time = Metrics.metric_calc(E, start_node, func=np.mean, weight='length')
    assert mean_time_t==mean_time

def test_calc_median(load_E):
    E = load_E
    start_node = list(E.G.nodes())[100]
    lngs = nx.single_source_dijkstra_path_length(E.G, start_node, weight='length')
    mean_time_t = np.median(list(lngs.values()))

    mean_time = Metrics.metric_calc(E, start_node, func=np.median, weight='length')
    assert mean_time_t==mean_time

def test_calc_ip_list():
    lst = [3,4,5,6,7,6,10,12,13,14]
    ip = Metrics.ip_calc(pd.Series(lst))
    assert 70.==ip