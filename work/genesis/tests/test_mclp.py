'''
Тесты для расчетов лучшей точки

`pytest tests/test_states.py -s`
'''

import pytest
from unittest.mock import Mock

import numpy as np
import osmnx as ox
import networkx as nx
import pandas as pd
import geopandas as gpd

from genesis.best_points import BestNodesFull, BestNodeHillClimbing
from genesis.core import BestPointsBase, StateBase, MetricBase
from genesis.mclp import BestNodesKoptG
from genesis.metrics import ArrivalTime, CoverIndex
from genesis.states import FirstArrivalUnitState


@pytest.fixture(scope='module')
def load_area():
    return gpd.read_file("tests/data/test_polygon.gpkg")

@pytest.fixture(scope='module')
def load_G_simplyfied():
    G = ox.load_graphml("tests/data/test_rng.ml")
    return ox.simplify_graph(G)


class TestBestNodesKoptG:
    '''
    Тесты для BestNodesFull
    '''
    def test_kopt_dicts(self, load_G_simplyfied):
        '''
        Базовый тест работоспособности
        '''
        G = load_G_simplyfied

        nodes = list(G.nodes())
        existed_units = {nodes[100]:'A', 
                nodes[200]:'B', 
                }
        new_units = {nodes[300]:'c',
                    nodes[400]:'d'}
        BNHC = BestNodeHillClimbing(state_function=FirstArrivalUnitState(),
                       metric_function=ArrivalTime(),
                       )

        BNG = BestNodesKoptG(state_function=FirstArrivalUnitState(),
                            metric_function=ArrivalTime(),
                            best_point_function=BNHC,
                            iterations=5,
                            )

        optimal_nodes, best_metric = BNG(env=G,
            static_nodes=existed_units,
            dynamic_nodes=new_units,
            )
        assert optimal_nodes == {2034401275: 'c', 2034401857: 'd'}
        assert best_metric  ==  5.4003346334809885

    def test_kopt_list(self, load_G_simplyfied):
        '''
        Базовый тест работоспособности
        '''
        G = load_G_simplyfied

        nodes = list(G.nodes())
        existed_units = [nodes[100], nodes[200]]
        new_units = [nodes[300], nodes[400]]
        BNHC = BestNodeHillClimbing(state_function=FirstArrivalUnitState(),
                       metric_function=ArrivalTime(),
                       )

        BNG = BestNodesKoptG(state_function=FirstArrivalUnitState(),
                            metric_function=ArrivalTime(),
                            best_point_function=BNHC,
                            iterations=5,
                            )

        optimal_nodes, best_metric = BNG(env=G,
            static_nodes=existed_units,
            dynamic_nodes=new_units,
            )
        assert optimal_nodes == [2034401275, 2034401857]
        assert best_metric  ==  5.4003346334809885






