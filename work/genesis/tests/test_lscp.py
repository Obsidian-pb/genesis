'''
Тесты для расчетов LSCP

`pytest tests/test_lscp.py -s`
'''

import pytest

import numpy as np
import osmnx as ox
import networkx as nx
import pandas as pd
import geopandas as gpd

from genesis.best_points import BestNodeHillClimbing
from genesis.lscp import LSCPCommon
from genesis.states import FirstArrivalUnitState
from genesis.metrics import ArrivalTime, CoverIndex
from genesis.mclp import BestNodesKoptG, BestNodesGA, BestNodesSA
from genesis.stop_cases import ItersStopCase
from genesis.point_selectors import GenesisNodeSelector, RandomNodesSelector, FarNodeSelector




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

class TestLSCPCommon:
    '''
    Тесты для LSCPCommon
    '''
    def test_lscp(self, load_G_simplyfied):
        '''
        Базовый тест работоспособности
        '''
        G = load_G_simplyfied

        nodes = list(G.nodes())
        existed_units = {nodes[100]: 'A',
                nodes[200]: 'B',
                }
        new_units = {nodes[300]: 'c',
                    nodes[400]: 'd'}

        # Функция расчета лучшего узла в графе
        BNHC = BestNodeHillClimbing(state_function = FirstArrivalUnitState(),
                                    metric_function = ArrivalTime())
        # Функция расчета лучшего размещения заданных узлов
        BNG = BestNodesKoptG(state_function = FirstArrivalUnitState(),
                            metric_function = ArrivalTime(),
                            best_point_function = BNHC,
                            iterations = 5,
                            )
        # Критерий остановки
        stop_case = ItersStopCase(max_iter_count = 2)
        # Селектор следующей точки
        point_selector = GenesisNodeSelector(state_function = FirstArrivalUnitState(),
                                            metric_function = ArrivalTime())


        # Сборка алгоритма
        genesis = LSCPCommon(mclp_function = BNG,
                            point_selector = point_selector,
                            stop_case_function = stop_case,
                            start_names_index = 5,
                            names_pattern='ПСЧ {}',
                            )

        # Расчет только динамические узлы
        best_dynamic_nodes, best_metric = genesis(env = G,
                                        dynamic_nodes = new_units,
                                        # static_nodes = existed_units,
                                        )
        assert best_dynamic_nodes == {290700367: 'd', 1577701962: 'c', 2034402108: 'ПСЧ 5', 2042076918: 'ПСЧ 6'}
        assert best_metric  ==  4.5251939000000005

        # Расчет динамические и статические узлы
        best_dynamic_nodes, best_metric = genesis(env = G,
                                        dynamic_nodes = new_units,
                                        static_nodes = existed_units,
                                        )
        assert best_dynamic_nodes == {2034401374: 'c', 290700367: 'd', 2034402108: 'ПСЧ 5', 2042076918: 'ПСЧ 6'}
        assert best_metric  ==  4.3977074946843855

# Расчет с пустым списком динамических узлов
# Расчет в пределах area
# расчет для ГА
# расчет для ИО
