"""
Тестовый запуск библиотеки
"""

# import osmnx as ox
# import networkx as nx
# from genesis import calculators
# import numpy as np
# from genesis.models import Environment
# from genesis.calculators import Metrics
from genesis.swiss_knife import ssfpl
import networkx as nx
import osmnx as ox
import logging as lg



# def test_calc_max():
#     G = ox.load_graphml("tests/data/test_rng.ml")
#     start_node = list(G.nodes())[100]

#     lngs = nx.single_source_dijkstra_path_length(G, start_node, weight='length')
#     max_time_node = max(lngs, key=lngs.get)
#     max_time_t = nx.dijkstra_path_length(G, start_node, max_time_node, weight='length')
#     max_time = calculators.max_time(G, start_node, weight='length')
#     print(max_time_t, max_time)
#     assert max_time_t==max_time

# def test_calc_mean():
#     G = ox.load_graphml("tests/data/test_rng.ml")
#     start_node = list(G.nodes())[100]
#     lngs = nx.single_source_dijkstra_path_length(G, start_node, weight='length')
#     # print(lngs.values())
#     mean_time_t = np.mean(list(lngs.values()))

#     mean_time = calculators.metric_calc(G, start_node, func=np.mean, weight='length')
#     assert mean_time_t==mean_time

def test_calc_ip10():
    E = Environment(ox.load_graphml("tests/data/test_rng.ml"))
    start_node = list(E.G.nodes())[100]
    lngs = nx.single_source_dijkstra_path_length(E.G, start_node, weight='length')
    covered = [1 if t<=10 else 0 for t in lngs.values()]
    ip_real = round(100*sum(covered)/len(covered), 2)

    ip_test = Metrics.calc_metric(E, 
                                   start_node, 
                                   path_function=ssfpl,
                                   metric_function=Metrics.calc_ip,
                                   weight='length')
    # lg.basicConfig(level=lg.DEBUG, filename="test_metrics.log", filemode="w")
    # lg.debug(f"{metric_function}: {val=}")
    # lg.debug("тестова запись")
    assert ip_real==ip_test


if __name__=='__main__':
    # test_calc_max()

    # lg.basicConfig(level=lg.INFO, filename="py_log.log") #,filemode="w")
    # lg.debug("A DEBUG Message")
    # lg.info("An INFO")
    # lg.warning("A WARNING")
    # lg.error("An ERROR Русский язык")
    # lg.critical("A message of CRITICAL severity")
    test_calc_ip10()