'''
Тесты для адаптеров

`pytest tests/adapters.py -s`
'''

import pytest

import numpy as np

import osmnx as ox
import networkx as nx
import pandas as pd
import geopandas as gpd

from genesis.best_points import BestNodeMonkey, BestNodesFull, BestNodeHillClimbing, BestNodesHalfDiameter

from genesis.metrics import ArrivalTime, CoverIndex
from genesis.states import FirstArrivalUnitState
from genesis.mclp import AdapterBLP2MCLP

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



class TestAdapterBLP2MCLP:
    '''
    Тесты для AdapterBLPtoMCLP
    '''
    def test_adapter_blp2mclp_hc(self, create_G):
        '''
        Тест для получения решений с помощью алгоритма BestNodeHillClimbing
        '''
        G = create_G
        start_node = list(G.nodes())[0]

        bnhc0 = BestNodeHillClimbing(
            state_function=FirstArrivalUnitState(),
            metric_function=ArrivalTime())
        best_node_bnhc0, best_metric_bnhc0 = bnhc0(G, start_point = start_node)

        bnhc1  = AdapterBLP2MCLP(
            BestNodeHillClimbing(
                state_function=FirstArrivalUnitState(),
                metric_function=ArrivalTime()
                )
            )
        best_node_bnhc1, best_metric_bnhc1 = bnhc1(G, dynamic_nodes={start_node: 'test'})

        assert best_node_bnhc0 == list(best_node_bnhc1.keys())[0]
        assert best_metric_bnhc0 == best_metric_bnhc1
        

    def test_adapter_blp2mclp_hc_area(self, create_G, create_points_mask):
        '''
        Тест для получения решений с помощью алгоритма BestNodeHillClimbing
        в пределах предопределенной зоны
        '''
        G = create_G
        points_mask = create_points_mask
        start_node = list(G.nodes())[0]

        bnhc0 = BestNodeHillClimbing(
            state_function=FirstArrivalUnitState(),
            metric_function=ArrivalTime())
        best_node_bnhc0, best_metric_bnhc0 = bnhc0(G, start_point = start_node, area = points_mask)

        bnhc1  = AdapterBLP2MCLP(
            BestNodeHillClimbing(
                state_function=FirstArrivalUnitState(),
                metric_function=ArrivalTime()
                )
            )
        best_node_bnhc1, best_metric_bnhc1 = bnhc1(G, points_mask, dynamic_nodes={start_node: 'test'})

        assert best_node_bnhc0 == list(best_node_bnhc1.keys())[0]
        assert best_metric_bnhc0 == best_metric_bnhc1


    def test_adapter_blp2mclp_wrong_type(self):
        '''
        Тест для получения решений с помощью алгоритма BestNodeHillClimbing
        с неправильным типом входных данных
        '''

        with pytest.raises(TypeError):
            _ = AdapterBLP2MCLP(
                nx.MultiDiGraph()
            )


