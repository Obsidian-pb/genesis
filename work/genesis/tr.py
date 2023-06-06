"""
Тестовый запуск библиотеки
"""

import osmnx as ox
import networkx as nx
from genesis import calcalators
import numpy as np


def test_calc_max():
    G = ox.load_graphml("tests/data/test_rng.ml")
    start_node = list(G.nodes())[100]

    lngs = nx.single_source_dijkstra_path_length(G, start_node, weight='length')
    max_time_node = max(lngs, key=lngs.get)
    max_time_t = nx.dijkstra_path_length(G, start_node, max_time_node, weight='length')
    max_time = calcalators.max_time(G, start_node, weight='length')
    print(max_time_t, max_time)
    assert max_time_t==max_time

def test_calc_mean():
    G = ox.load_graphml("tests/data/test_rng.ml")
    start_node = list(G.nodes())[100]
    lngs = nx.single_source_dijkstra_path_length(G, start_node, weight='length')
    # print(lngs.values())
    mean_time_t = np.mean(list(lngs.values()))

    mean_time = calcalators.metric_calc(G, start_node, func=np.mean, weight='length')
    assert mean_time_t==mean_time


if __name__=='__main__':
    # test_calc_max()

    test_calc_mean()