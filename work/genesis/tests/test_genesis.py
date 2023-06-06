import osmnx as ox
import networkx as nx
from genesis.tools import metrics


def test_calc_max():
    G = ox.load_graphml("tests/data/test_rng.ml")
    start_node = list(G.nodes())[100]
    lngs = nx.single_source_dijkstra_path_length(G, start_node, weight='length')
    max_time_node = max(lngs, key=lngs.get)
    max_time_t = nx.dijkstra_path_length(G, start_node, max_time_node, weight='length')

    max_time = metrics.max_time(G, start_node, weight='length')
    assert max_time_t==max_time

