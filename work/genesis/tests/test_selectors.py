'''
Тесты для расчетов селекторов узлов

`pytest tests/test_selectors.py -s`
'''

import pytest

import osmnx as ox
import networkx as nx
import numpy as np
import pandas as pd
import geopandas as gpd

from genesis.metrics import MetricBase, ArrivalTime, CoverIndex
from genesis.point_selectors import RandomNodesSelector, WorstNodeSelector
from genesis.states import FirstArrivalUnitState
from genesis.swiss_knife import MSF






@pytest.fixture(scope='module')
def load_G():
    return ox.load_graphml("tests/data/test_rng.ml")

@pytest.fixture(scope='module')
def load_area():
    return gpd.read_file("tests/data/test_polygon.gpkg")

@pytest.fixture(scope='module')
def load_G_simplyfied():
    G = ox.load_graphml("tests/data/test_rng.ml")
    return ox.simplify_graph(G)


class TestRandomNodesSelector:
    '''
    Тесты для RandomNodesSelector
    '''
    def test_random_nodes_selector(self, load_G_simplyfied):
        '''
        Тесты базового расчета
        '''
        G = load_G_simplyfied

        nodes = list(G.nodes())
        all_units = {
            nodes[100]:'A',
            nodes[200]:'B',
            nodes[300]:'C',
            nodes[400]:'D',
        }
        new_node = RandomNodesSelector()(G, all_units)

        assert len(new_node) == 1
        assert isinstance(new_node[0], int)
        assert new_node[0] in nodes
        assert not new_node[0] in list(all_units.keys())

    def test_random_nodes_selector_data(self, load_G_simplyfied, load_area):
        '''
        Тест передачи некорректных данных
        '''
        G = nx.Graph()
        G.add_node(1)
        G.add_node(2)
        G.add_node(3)
        G.add_node(4)
        G.add_edge(1,2)
        G.add_edge(2,3)
        G.add_edge(3,4)
        nodes = list(G.nodes())
        all_units = {
            nodes[1]:'A',
            nodes[2]:'B',
        }
        with pytest.raises(TypeError):
            RandomNodesSelector()(G, all_units)

        G = load_G_simplyfied
        nodes = list(G.nodes())
        all_units = [
            nodes[100],
            nodes[200],
        ]
        with pytest.raises(TypeError):
            RandomNodesSelector()(G, all_units)

        all_units = {
            nodes[100]:'A',
            nodes[200]:'B',
            nodes[300]:'C',
            nodes[400]:'D',
        }
        points_mask = [1,2,3,4,5,6,7,8,9]
        with pytest.raises(TypeError):
            RandomNodesSelector()(G, all_units, area=points_mask)

        area = load_area
        nodes_g = ox.graph_to_gdfs(G, edges=False)
        points_mask = nodes_g.within(area.iloc[0].geometry)
        with pytest.raises(ValueError):
            RandomNodesSelector()(G, all_units, area=points_mask, k=0)


# Тесты:
# работоспособность в целом
# приемлемость данных
# узел находится в area
# для детерминированных расчтов - ИД узла
