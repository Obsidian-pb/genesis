'''
Тесты калькуляторов времен прибытия
'''

import pytest

import networkx as nx
# import geopandas as gpd
import pandas as pd

from genesis.features import RoadNetworkGraph, DislocationProfile, SpeedProfile, ArrivaLProfile
from genesis.morphers import MorphersGraph, MorphersSpatialFeature
from genesis.calculators import Arrivals
from genesis.models import Environment
from genesis.environments import CommonEnvironment


@pytest.fixture(scope='module')
def load_E():
    E = Environment(path='tests/data/')
    E.add_features(
        [
            RoadNetworkGraph(path='test_rng.ml'),
            DislocationProfile(),
            SpeedProfile()
        ]
    ).load()
    E.crs = E['RNG'].crs
    return E


class TestCalcAP():
    def test_calc_ap(self, load_E):
        '''Тест расчета ПП с использованием базового Environment'''
        E = load_E

        MorphersGraph.add_edge_travel_times(E['RNG'].G, E['SP'])
        MorphersSpatialFeature.add_nearest_node(E['DP'], E['RNG'])
        AP = Arrivals.calc_AP(E, path_function=nx.multi_source_dijkstra, AP_name='AP_test')
        assert isinstance(AP, ArrivaLProfile)
        assert round(AP.data.loc[1545611804]['arrival_time'],2) == round(1.027307,2)
        assert AP.data.loc[2042076383]['unit'] == 'ОП ПСЧ-1'
        assert len(AP['ОП ПСЧ-1']) == 2566
        assert len(AP['ПСЧ-1']) == 2938


    def test_calc_ap_custom_names(self):
        '''Тест расчета ПП с использованием измененных имен'''
        E = Environment(path='tests/data/')
        E.add_features(
            [
                RoadNetworkGraph(name='RNG_1', path='test_rng.ml'),
                DislocationProfile(name='DP_1'),
                SpeedProfile(name='SP_1')
            ]
        ).load()
        E.crs = E['RNG_1'].crs

        MorphersGraph.add_edge_travel_times(E['RNG_1'].G, E['SP_1'])
        MorphersSpatialFeature.add_nearest_node(E['DP_1'], E['RNG_1'], node_field='nf')
        AP = Arrivals.calc_AP(E,
                                  path_function=nx.multi_source_dijkstra,
                                  AP_name='AP_test',
                                  RNG_name='RNG_1',
                                  DP_name='DP_1',
                                  DP_node_field='nf'
                                  )
        assert isinstance(AP, ArrivaLProfile)