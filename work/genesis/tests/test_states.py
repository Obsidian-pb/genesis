'''
Тесты для расчетов состояния среды

`pytest tests/test_states.py -s`
'''

import pytest

import numpy as np

import osmnx as ox
import networkx as nx
import pandas as pd
import geopandas as gpd

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




class TestMetricsArrivalTime:
    '''
    Тестирование расчета состояния среды по времени прибытия первого подразделения
    '''
    def test_first_arr_unit_calc_single_node(self, load_G):

        G = load_G
        start_points = [list(G.nodes())[1000]]

        times, _ = FirstArrivalUnitState()(env=G, points=start_points)
        len_t = 5504
        assert isinstance(times, pd.Series)
        assert len_t==len(times)

    def test_first_arr_unit_calc_multi_nodes_from_list(self, load_G):

        G = load_G
        ndl = list(G.nodes())
        start_points = [ndl[1000], ndl[2000], ndl[3000]]

        times, _ = FirstArrivalUnitState()(env=G, points=start_points)
        len_t = 5504
        assert isinstance(times, pd.Series)
        assert len_t==len(times)    

    def test_first_arr_unit_calc_multi_nodes_from_dict(self, load_G):

        G = load_G
        ndl = list(G.nodes())
        start_points = {ndl[100]:'A', 
                        ndl[2000]:'B', 
                        ndl[3000]:'C'}

        times, _ = FirstArrivalUnitState()(env=G, points=start_points)
        len_t = 5504
        assert isinstance(times, pd.Series)
        assert len_t==len(times)  

    def test_first_arr_unit_calc_multi_nodes_from_dict_unique(self, load_G):

        G = load_G
        ndl = list(G.nodes())
        start_points = {ndl[100]:'A', 
                        ndl[2000]:'B', 
                        ndl[3000]:'C'}

        times, nearest = FirstArrivalUnitState()(env=G, points=start_points)
        len_t = 5504
        units=len(start_points)
        assert isinstance(times, pd.Series)
        assert len_t==len(times)
        assert units == len(nearest.unique())

    def test_first_arr_unit_calc_single_nodes_with_cutoff(self, load_G):
        
        G = load_G
        start_points = [list(G.nodes())[1000]]

        times, _ = FirstArrivalUnitState()(env=G, points=start_points, cutoff=5)
        len_t = 1126
        assert len_t==len(times)

    def test_with_custom_state_algorithm(self, load_G):

        def multi_source_dijkstra_reversed(G, **kwargs):
            G = nx.reverse(G.copy())
            return nx.multi_source_dijkstra(G=G, **kwargs)
        
        G = load_G
        start_points = [list(G.nodes())[1000]]

        times, _ = FirstArrivalUnitState(multi_source_dijkstra_reversed)(env=G, points=start_points)
        time_max_t = 20.199067214285723
        assert time_max_t==np.max(times)

    def test_first_arr_unit_calc_single_nodes_in_area(self, load_G, load_area):

        G = load_G
        area = load_area
        start_points = [list(G.nodes())[2000]]
        nodes = ox.graph_to_gdfs(G, edges=False)
        points_mask = nodes.within(area.iloc[0].geometry)

        times, _ = FirstArrivalUnitState()(env=G, points=start_points, area=points_mask)
        len_t = 2237
        assert len_t==len(times)
