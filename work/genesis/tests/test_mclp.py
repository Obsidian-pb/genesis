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
        existed_units = {nodes[100]: 'A',
                nodes[200]: 'B',
                }
        new_units = {nodes[300]: 'c',
                    nodes[400]: 'd'}
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

    def test_static_immutable(self, load_G_simplyfied):
        '''
        Тест неизменяемости статических узлов
        '''
        class IterFunc:
            def __init__(self):
                pass
            def __call__(self, **kwds):
                self.static_nodes = kwds.get('static_nodes')
        iter_func = IterFunc()

        G = load_G_simplyfied

        nodes = list(G.nodes())
        existed_units = {nodes[100]: 'A',
                nodes[200]: 'B',
                }
        new_units = {nodes[300]: 'c',
                    nodes[400]: 'd'}
        BNHC = BestNodeHillClimbing(state_function=FirstArrivalUnitState(),
                       metric_function=ArrivalTime(),
                       )

        BNG = BestNodesKoptG(state_function=FirstArrivalUnitState(),
                            metric_function=ArrivalTime(),
                            best_point_function=BNHC,
                            iterations=5,
                            )

        _, _ = BNG(env=G,
            static_nodes=existed_units,
            dynamic_nodes=new_units,
            before_iters_start_function=iter_func,
            )
        assert iter_func.static_nodes == existed_units


    def test_area_calc(self, load_G_simplyfied, load_area):
        '''
        Тест расчета в пределах некоторой области
        '''
        G = load_G_simplyfied

        nodes = list(G.nodes())
        existed_units = {nodes[100]: 'A',
                nodes[200]: 'B',
                }
        new_units = {nodes[300]: 'c',
                    nodes[400]: 'd'}
        
        area = load_area
        nodes = ox.graph_to_gdfs(G, edges=False)
        points_mask = nodes.within(area.iloc[0].geometry)

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
            area=points_mask,
            )
        assert optimal_nodes == {2034401275: 'c', 2034401663: 'd'}
        assert best_metric  ==  3.011331473882282

    def test_reloab_bnf(self, load_G_simplyfied):
        '''
        Тест использования перегруженной функции
        '''
        class BestNodeHillClimbing_MaxMean(BestNodeHillClimbing):
            def __init__(self, 
                        state_function: StateBase, 
                        metric_function: MetricBase = None, 
                        appr_val: float = 0.95, 
                        all_neighbors: bool = False, 
                        **kwargs) -> None:
                super().__init__(state_function, metric_function, appr_val, all_neighbors, **kwargs)

            def __call__(self, env: nx.MultiDiGraph, 
                        area: pd.Series = None, 
                        start_node: int = None, 
                        **kwargs):
                bnch_max = BestNodeHillClimbing(state_function=self.state_function,
                                                metric_function=ArrivalTime(np.max), appr_val=self.appr_val, all_neighbors=self.all_neighbors)
                bnch_mean = BestNodeHillClimbing(state_function=self.state_function,
                                                metric_function=ArrivalTime(), appr_val=self.appr_val, all_neighbors=self.all_neighbors)

                best_node, best_metric = bnch_max(env=env, area=area, start_node=start_node)
                best_node, best_metric = bnch_mean(env=env, area=area, start_node=best_node)
                return best_node, best_metric
            
        G = load_G_simplyfied

        nodes = list(G.nodes())
        existed_units = {nodes[100]: 'A',
                nodes[200]: 'B',
                }
        new_units = {nodes[300]: 'c',
                    nodes[400]: 'd'}
        BNHC = BestNodeHillClimbing_MaxMean(state_function=FirstArrivalUnitState())

        BNG = BestNodesKoptG(state_function=FirstArrivalUnitState(),
                            metric_function=ArrivalTime(),
                            best_point_function=BNHC,
                            iterations=5,
                            )

        optimal_nodes, best_metric = BNG(env=G,
            static_nodes=existed_units,
            dynamic_nodes=new_units,
            )
        assert optimal_nodes == {2034401362: 'c', 2034401857: 'd'}
        assert best_metric  ==  5.3976885050203025

    def test_max_mean_cons(self, load_G_simplyfied):
        '''
        Тест расчета последовательно метриками Max Mean
        '''
        G = load_G_simplyfied

        nodes = list(G.nodes())
        existed_units = {nodes[100]: 'A',
                nodes[200]: 'B',
                }
        new_units = {nodes[300]: 'c',
                    nodes[400]: 'd'}

        # Расчет метрикой max_time
        BNHC_max = BestNodeHillClimbing(state_function=FirstArrivalUnitState(),
                            metric_function=ArrivalTime(np.max),
                            )
        BNG_max = BestNodesKoptG(state_function=FirstArrivalUnitState(),
                            metric_function=ArrivalTime(),
                            best_point_function=BNHC_max,
                            iterations=5,
                            )
        optimal_nodes, best_metric = BNG_max(env=G,
            dynamic_nodes=new_units,
            )
        # Расчет метрикой mean_time
        BNHC_mean = BestNodeHillClimbing(state_function=FirstArrivalUnitState(),
                            metric_function=ArrivalTime(),
                            )
        BNG_mean = BestNodesKoptG(state_function=FirstArrivalUnitState(),
                            metric_function=ArrivalTime(),
                            best_point_function=BNHC_mean,
                            iterations=5,
                            )
        optimal_nodes, best_metric = BNG_mean(env=G,
            static_nodes=existed_units,
            dynamic_nodes=optimal_nodes,
            )
        
        assert optimal_nodes == {6211105430: 'c', 2034401777: 'd'}
        assert best_metric  ==  5.012592071760797