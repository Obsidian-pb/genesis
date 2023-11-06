'''
Тесты для алгоритмов

`pytest tests/test_algorithms.py -s`
'''

import pytest

import osmnx as ox
import networkx as nx
import numpy as np
# import pandas as pd


from genesis.metrics import *
from genesis.swiss_knife import msfpl
from genesis.algorithms import Graphs


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


# Здесь bnf = best node full. Алгоритм поиска наилучшего узла полным перебором

class TestBNF:
    def test_bnf_basic_mean(self, create_G):
        G = create_G
        best_node, best_val = Graphs.get_best_node_full(G,
                            path_function=msfpl,
                            metric_function=np.mean
                            )
        assert best_node==1
        assert best_val==8.67

    def test_bnf_basic_max(self, create_G):
        G = create_G
        best_node, best_val = Graphs.get_best_node_full(G,
                            path_function=msfpl,
                            metric_function=np.max
                            )
        assert best_node==4
        assert best_val==17

    def test_bnf_basic_ip10(self, create_G):
        G = create_G
        best_node, best_val = Graphs.get_best_node_full(G,
                            path_function=msfpl,
                            metric_function=cover_index(),
                            reduce=False
                            )
        assert best_node==1
        assert best_val==66.67

    def test_bnf_basic_ip20(self, create_G):
        G = create_G
        best_node, best_val = Graphs.get_best_node_full(G,
                            path_function=msfpl,
                            metric_function=cover_index(ip_val=20),
                            reduce=False
                            )
        assert best_node==4
        assert best_val==100.0

    def test_bnf_basic_ip10_allapp(self, create_G):
        '''
        Тест расчета при условии что в результат включаются все узлы, в том числе и слабосвязанные
        '''
        G = create_G
        best_node, best_val = Graphs.get_best_node_full(G,
                            path_function=msfpl,
                            metric_function=cover_index(),
                            appr_val=0,
                            reduce=False
                            )
        assert best_node==9
        assert best_val==100.0

    def test_bnf_basic_mean_fromlist(self, create_G):
        '''
        Определение лучшего узла по метрике среднего времени следования из указанного списка
        '''
        G = create_G
        nodes_list=[1,2,5,8]
        best_node, best_val = Graphs.get_best_node_full(G,
                            path_function=msfpl,
                            metric_function=np.mean,
                            possible_nodes=nodes_list
                            )
        assert best_node==1
        assert best_val==8.67

    def test_bnf_basic_mean_fromlist_badnodes(self, create_G):
        '''
        Определение лучшего узла по метрике среднего времени следования из указанного списка. 
        Узлы слабо связаны
        '''
        G = create_G
        nodes_list=[2,5,8]
        best_node, best_val = Graphs.get_best_node_full(G,
                            path_function=msfpl,
                            metric_function=np.mean,
                            possible_nodes=nodes_list
                            )
        assert best_node==None
        assert best_val==None

    def test_bnf_basic_mean_fromlist_badnodes_05(self, create_G):
        '''
        Определение лучшего узла по метрике среднего времени следования из указанного списка. 
        Узлы слабо связаны, но при условии покрытия 0,5 узлов графа, некоторые из них могут быть учтены.
        '''
        G = create_G
        nodes_list=[2,5,8]
        best_node, best_val = Graphs.get_best_node_full(G,
                            path_function=msfpl,
                            metric_function=np.mean,
                            appr_val=0.5,
                            possible_nodes=nodes_list
                            )
        assert best_node==2
        assert best_val==8.69

    def test_bnf_basic_mean_fromlist_badnodes_0(self, create_G):
        '''
        Определение лучшего узла по метрике среднего времени следования из указанного списка. 
        Узлы слабо связаны, но все из них могут быть учтены.
        '''
        G = create_G
        nodes_list=[2,5,8]
        best_node, best_val = Graphs.get_best_node_full(G,
                            path_function=msfpl,
                            metric_function=np.mean,
                            appr_val=0,
                            possible_nodes=nodes_list
                            )
        assert best_node==8
        assert best_val==6.25


