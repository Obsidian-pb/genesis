'''
Тесты для расчетов лучшей точки

`pytest tests/test_states.py -s`
'''

import pytest

import numpy as np

import osmnx as ox
import networkx as nx
import pandas as pd
import geopandas as gpd

from genesis.best_points import BestNodesFull, BestNodeHillClimbing
from genesis.metrics import ArrivalTime, CoverIndex
from genesis.states import FirstArrivalUnitState

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

@pytest.fixture(scope='module')
def create_points_mask():
    points_mask = {
        1:False,
        2:False,
        3:False,
        4:True,
        5:True,
        6:True,
        7:True,
        8:True,
        9:True,
        10:True,
        11:True,
        12:False,
        13:False,
        14:False,
        15:False
    }
    return pd.Series(points_mask)


class TestBestNodesFull:
    '''
    Тесты для BestNodesFull
    '''
    def test_best_nodes_full(self, create_G):
        '''
        Базовый тест работоспособности
        '''
        G = create_G
        best_nodes, best_metric = BestNodesFull(FirstArrivalUnitState(), ArrivalTime())(G)
        assert best_nodes==[1]
        assert best_metric==9.666666666666666
        best_nodes, best_metric = BestNodesFull(FirstArrivalUnitState(), ArrivalTime(np.max))(G)
        assert best_nodes==[4]
        assert best_metric==18.0
        best_nodes, best_metric = BestNodesFull(FirstArrivalUnitState(), CoverIndex())(G)
        assert best_nodes==[1]
        assert best_metric==60.0
        best_nodes, best_metric = BestNodesFull(FirstArrivalUnitState(), CoverIndex(20))(G)
        assert best_nodes==[4]
        assert best_metric==100.0

    def test_best_nodes_full_in_area(self, create_G, create_points_mask):
        '''
        Базовый тест работоспособности в пределах некоторой области
        '''
        G = create_G
        points_mask = create_points_mask
        best_nodes, best_metric = BestNodesFull(FirstArrivalUnitState(), ArrivalTime())(G, area=points_mask)
        assert best_nodes==[3]
        assert best_metric==8.0
        best_nodes, best_metric = BestNodesFull(FirstArrivalUnitState(), ArrivalTime(np.max))(G, area=points_mask)
        assert best_nodes==[3, 4]
        assert best_metric==13.0
        best_nodes, best_metric = BestNodesFull(FirstArrivalUnitState(), CoverIndex())(G, area=points_mask)
        assert best_nodes==[2]
        assert best_metric==85.71428571428571
        best_nodes, best_metric = BestNodesFull(FirstArrivalUnitState(), CoverIndex(20))(G, area=points_mask)
        assert best_nodes==[1,2,3,4]
        assert best_metric==100.0
        
    def test_best_nodes_full_list_nodes(self, create_G, create_points_mask):
        '''
        Базовый тест работоспособности
        для списка узлов
        '''
        G = create_G
        nodes_for_calc = [1,4,7,9,10,11,12]
        best_nodes, best_metric = BestNodesFull(FirstArrivalUnitState(),
                                                ArrivalTime())(G,
                                                               nodes_list=nodes_for_calc)
        assert best_nodes==[1]
        assert best_metric==9.666666666666666
        best_nodes, best_metric = BestNodesFull(FirstArrivalUnitState(),
                                                ArrivalTime(np.max))(G,
                                                                     nodes_list=nodes_for_calc)
        assert best_nodes==[4]
        assert best_metric==18.0
        best_nodes, best_metric = BestNodesFull(FirstArrivalUnitState(),
                                                CoverIndex())(G,
                                                              nodes_list=nodes_for_calc)
        assert best_nodes==[1]
        assert best_metric==60.0
        best_nodes, best_metric = BestNodesFull(FirstArrivalUnitState(), CoverIndex(20))(G,
                                                                                         nodes_list=nodes_for_calc)
        assert best_nodes==[4]
        assert best_metric==100.0

    def test_best_nodes_full_list_nodes_in_area(self, create_G, create_points_mask):
        '''
        Базовый тест работоспособности в пределах некоторой области
        для списка узлов
        '''
        G = create_G
        nodes_for_calc = [1,4,5,6,7,8,14]
        points_mask = create_points_mask
        best_nodes, best_metric = BestNodesFull(FirstArrivalUnitState(),
                                                ArrivalTime())(G,
                                                               area=points_mask,
                                                               nodes_list=nodes_for_calc)
        assert best_nodes==[4]
        assert best_metric==8.125
        best_nodes, best_metric = BestNodesFull(FirstArrivalUnitState(),
                                                ArrivalTime(np.max))(G,
                                                                     area=points_mask,
                                                                     nodes_list=nodes_for_calc)
        assert best_nodes==[4]
        assert best_metric==13.0
        best_nodes, best_metric = BestNodesFull(FirstArrivalUnitState(),
                                                CoverIndex())(G,
                                                              area=points_mask,
                                                              nodes_list=nodes_for_calc)
        assert best_nodes==[1]
        assert best_metric==75.0
        best_nodes, best_metric = BestNodesFull(FirstArrivalUnitState(),
                                                CoverIndex(20))(G,
                                                                area=points_mask,
                                                                nodes_list=nodes_for_calc)
        assert best_nodes==[1,4]
        assert best_metric==100.0

    def test_best_nodes_full_1(self, create_G):
        '''
        Тест работоспособности при условии,
        что из узла можно попасть в любой другой узел графа (appr_val=100%)
        '''
        G = create_G
        best_nodes, best_metric = BestNodesFull(FirstArrivalUnitState(),
                                                ArrivalTime(),
                                                appr_val=1)(env=G)
        assert best_nodes==[1]
        assert best_metric==9.666666666666666

class TestBestNodeHillClimbing:
    '''
    Тесты для BestNodeHillClimbing
    '''
    def test_bnhc(self, create_G):
        '''
        Простой тест 
        '''
        G = create_G

        best_nodes, best_metric = BestNodeHillClimbing(FirstArrivalUnitState(), ArrivalTime())(G)
        assert best_nodes == 1
        assert best_metric == 9.666666666666666
        best_nodes, best_metric = BestNodeHillClimbing(FirstArrivalUnitState(), ArrivalTime(np.max))(G)
        assert best_nodes == 4
        assert best_metric == 18.0
        best_nodes, best_metric = BestNodeHillClimbing(FirstArrivalUnitState(), CoverIndex())(G)
        assert best_nodes == 1
        assert best_metric == 60.0
        best_nodes, best_metric = BestNodeHillClimbing(FirstArrivalUnitState(), CoverIndex(20))(G)
        assert best_nodes == 4
        assert best_metric == 100.0

    def test_bnhc_area(self, create_G, create_points_mask):
        '''
        Тест работоспособности в пределах некоторой области
        '''
        G = create_G
        points_mask = create_points_mask
        best_nodes, best_metric = BestNodeHillClimbing(FirstArrivalUnitState(), ArrivalTime())(G, area=points_mask)
        assert best_nodes == 3
        assert best_metric == 8.0
        best_nodes, best_metric = BestNodeHillClimbing(FirstArrivalUnitState(), ArrivalTime(np.max))(G, area=points_mask)
        assert best_nodes == 3
        assert best_metric == 13.0
        best_nodes, best_metric = BestNodeHillClimbing(FirstArrivalUnitState(), CoverIndex())(G, area=points_mask)
        assert best_nodes == 2
        assert best_metric == 85.71428571428571
        best_nodes, best_metric = BestNodeHillClimbing(FirstArrivalUnitState(), CoverIndex(20))(G, area=points_mask)
        assert best_nodes == 1
        assert best_metric == 100.0

    def test_bnhc_start_node(self, create_G):
        '''
        Тест расчета для указанного стартового узла
        '''
        G = create_G
        node_for_calc = 1

        best_nodes, best_metric = BestNodeHillClimbing(FirstArrivalUnitState(), ArrivalTime())(G, start_node=node_for_calc)
        assert best_nodes == 1
        assert best_metric ==  9.666666666666666
        best_nodes, best_metric = BestNodeHillClimbing(FirstArrivalUnitState(), ArrivalTime(np.max))(G, start_node=node_for_calc)
        assert best_nodes == 4
        assert best_metric == 18.0
        best_nodes, best_metric = BestNodeHillClimbing(FirstArrivalUnitState(), CoverIndex())(G, start_node=node_for_calc)
        assert best_nodes == 1
        assert best_metric == 60.0
        best_nodes, best_metric = BestNodeHillClimbing(FirstArrivalUnitState(), CoverIndex(20))(G, start_node=node_for_calc)
        assert best_nodes == 4
        assert best_metric == 100.0

    def test_bnhc_area_start(self, create_G, create_points_mask):
        '''
        Тест расчета для указанного стартового узла 
        в пределах некоторой области
        '''
        G = create_G
        points_mask = create_points_mask
        node_for_calc = 1

        best_nodes, best_metric = BestNodeHillClimbing(FirstArrivalUnitState(), ArrivalTime())(G, area=points_mask, start_node=node_for_calc)
        assert best_nodes == 3
        assert best_metric == 8.0
        best_nodes, best_metric = BestNodeHillClimbing(FirstArrivalUnitState(), ArrivalTime(np.max))(G, area=points_mask, start_node=node_for_calc)
        assert best_nodes == 3
        assert best_metric == 13.0
        best_nodes, best_metric = BestNodeHillClimbing(FirstArrivalUnitState(), CoverIndex())(G, area=points_mask, start_node=node_for_calc)
        assert best_nodes == 2
        assert best_metric == 85.71428571428571
        best_nodes, best_metric = BestNodeHillClimbing(FirstArrivalUnitState(), CoverIndex(20))(G, area=points_mask, start_node=node_for_calc)
        assert best_nodes == 1
        assert best_metric == 100.0

    def test_bnhc_G(self, load_G):
        '''
        Тест расчета для большого графа
        '''
        G = load_G
        bnhc = BestNodeHillClimbing(FirstArrivalUnitState(), ArrivalTime())
        best_nodes, best_metric = bnhc(env=G)
        assert best_nodes == 426923808
        assert best_metric == 8.355415617070701
        bnhc = BestNodeHillClimbing(FirstArrivalUnitState(), ArrivalTime(np.max))
        best_nodes, best_metric = bnhc(env=G)
        assert best_nodes == 2034401823
        assert best_metric == 18.917574142857145
        bnhc = BestNodeHillClimbing(FirstArrivalUnitState(), CoverIndex())
        best_nodes, best_metric = bnhc(env=G)
        assert best_nodes == 4116048897
        assert best_metric == 60.247093023255815
        bnhc = BestNodeHillClimbing(FirstArrivalUnitState(), CoverIndex(20))
        best_nodes, best_metric = bnhc(env=G)
        assert best_nodes == 2034401903
        assert best_metric == 100.0

    def test_bnhc_G_area(self, load_G, load_area):
        '''
        Тест расчета для большого графа
        при учете только некоторой области
        '''
        G = load_G
        area = load_area
        nodes = ox.graph_to_gdfs(G, edges=False)
        points_mask = nodes.within(area.iloc[0].geometry)

        bnhc = BestNodeHillClimbing(FirstArrivalUnitState(), ArrivalTime())
        best_nodes, best_metric = bnhc(env=G,  area=points_mask)
        assert best_nodes == 1577701962
        assert best_metric == 4.328401644772975
        bnhc = BestNodeHillClimbing(FirstArrivalUnitState(), ArrivalTime(np.max))
        best_nodes, best_metric = bnhc(env=G,  area=points_mask)
        assert best_nodes == 2034401285
        assert best_metric == 11.544648285714286
        bnhc = BestNodeHillClimbing(FirstArrivalUnitState(), CoverIndex())
        best_nodes, best_metric = bnhc(env=G,  area=points_mask)
        assert best_nodes == 2034401285
        assert best_metric == 98.83772910147519
        bnhc = BestNodeHillClimbing(FirstArrivalUnitState(), CoverIndex(20))
        best_nodes, best_metric = bnhc(env=G,  area=points_mask)
        assert best_nodes == 290700344
        assert best_metric == 100.0

    def test_bnhc_mm(self, load_G, load_area):
        '''
        Тест перегрузки функции на примере последовательности метрик
        max+mean
        '''
        def BestNodeHillClimbing_MaxMean(env, area=None):
            bnch_max = BestNodeHillClimbing(state_function=FirstArrivalUnitState(), metric_function=ArrivalTime(np.max))
            bnch_mean = BestNodeHillClimbing(state_function=FirstArrivalUnitState(), metric_function=ArrivalTime())

            best_node, best_metric = bnch_max(env=env, area=area)
            best_node, best_metric = bnch_mean(env=env, start_node=best_node, area=area)

            return best_node, best_metric

        G = load_G
        area = load_area
        nodes = ox.graph_to_gdfs(G, edges=False)
        points_mask = nodes.within(area.iloc[0].geometry)

        best_node, best_metric = BestNodeHillClimbing_MaxMean(G)
        assert best_node == 426923808
        assert best_metric == 8.355415617070701

        best_node, best_metric = BestNodeHillClimbing_MaxMean(G, area=points_mask)
        assert best_node == 1577701962
        assert best_metric == 4.328401644772975

