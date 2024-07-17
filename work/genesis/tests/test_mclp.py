'''
Тесты для расчетов MCLP

`pytest tests/test_mclp.py -s`
'''

import pytest

import numpy as np
import osmnx as ox
import networkx as nx
import pandas as pd
import geopandas as gpd

from genesis.best_points import BestNodeHillClimbing
from genesis.core import StateBase, MetricBase
from genesis.mclp import BestNodesGA, BestNodesKoptG, BestNodesSA
from genesis.metrics import ArrivalTime, CoverIndex
from genesis.states import FirstArrivalUnitState



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


class TestGA:
    '''
    Тесты для GA
    '''
    def test_ga(self, load_G):
        '''
        Тест GA. Основной.
        '''
        G = load_G

        nodes = list(G.nodes())
        existed_units = {nodes[1000]: 'A',
                nodes[2000]: 'B',
                }
        new_units = {nodes[3000]: 'c',
                    nodes[4000]: 'd'}

        BNGA = BestNodesGA(state_function=FirstArrivalUnitState(),
                            metric_function=ArrivalTime(),
                            epochs=5,
                            )

        _, best_metric = BNGA(env=G,
            static_nodes=existed_units,
            dynamic_nodes=new_units,
            )

        assert best_metric <= 5.5

    def test_ga_area(self, load_G, load_area):
        '''
        Тест GA в пределах некоторой области
        '''
        G = load_G
        area = load_area
        nodes = ox.graph_to_gdfs(G, edges=False)
        points_mask = nodes.within(area.iloc[0].geometry)

        nodes = list(G.nodes())
        existed_units = {nodes[1000]: 'A',
                nodes[2000]: 'B',
                }
        new_units = {nodes[3000]: 'c',
                    nodes[4000]: 'd'}

        BNGA = BestNodesGA(state_function=FirstArrivalUnitState(),
                            metric_function=ArrivalTime(),
                            epochs=5,
                            )

        _, best_metric = BNGA(env=G,
            static_nodes=existed_units,
            dynamic_nodes=new_units,
            area=points_mask,
            )

        assert best_metric <= 4


    def test_ga_cover_index(self, load_G):
        '''
        Тест GA. Метрика: ИП-5
        Только динамические узлы.
        '''
        G = load_G

        nodes = list(G.nodes())
        new_units = {nodes[3000]: 'c',
                    nodes[4000]: 'd'}

        BNGA = BestNodesGA(state_function=FirstArrivalUnitState(),
                            metric_function=CoverIndex(5),
                            epochs=10,
                            )

        _, best_metric = BNGA(env=G,
            dynamic_nodes=new_units,
            )

        assert best_metric > 30


    def test_ga_many_units(self, load_G):
        '''
        Тест ГА для множества подразделений
        '''
        G = load_G
        nodes = list(G.nodes())
        new_units = {nodes[1000]:'a',
                    nodes[1500]:'b',
                    nodes[2000]:'c',
                    nodes[2500]:'d',
                    nodes[3000]:'e',
                    nodes[3500]:'f',
                    nodes[4000]:'g',}

        BNGA = BestNodesGA(FirstArrivalUnitState(),
                        ArrivalTime(),
                        population_size=20,
                        elite_size=10,
                        epochs=5,
                        )

        _, best_metric = BNGA(env=G, 
                                        dynamic_nodes=new_units
                                        )
        assert best_metric < 4.76783714891767


class TestSA:
    '''
    Тесты для реализации имитации отжига
    '''
    def test_sa(self, load_G):
        '''
        Тест SA. Основной.
        '''
        G = load_G

        nodes = list(G.nodes())
        existed_units = {nodes[1000]: 'A',
                nodes[2000]: 'B',
                }
        new_units = {nodes[3000]: 'c',
                    nodes[4000]: 'd'}

        BNSA = BestNodesSA(FirstArrivalUnitState(),
                    ArrivalTime(),
                    end_temperature = 0.01,
                    )

        best_nodes, best_metric = BNSA(env=G, 
                                  static_nodes=existed_units,
                                  dynamic_nodes=new_units,
                                  )

        assert best_metric <= 7.3
        assert isinstance(best_nodes, dict)
        assert isinstance(best_metric, float)

    def test_sa_area(self, load_G, load_area):
        '''
        Тест SA в пределах некоторой области
        '''
        G = load_G
        area = load_area
        nodes = ox.graph_to_gdfs(G, edges=False)
        points_mask = nodes.within(area.iloc[0].geometry)

        nodes = list(G.nodes())
        existed_units = {nodes[1000]: 'A',
                nodes[2000]: 'B',
                }
        new_units = {nodes[3000]: 'c',
                    nodes[4000]: 'd'}

        BNSA = BestNodesSA(FirstArrivalUnitState(),
                    ArrivalTime(),
                    end_temperature = 0.01,
                    )

        _, best_metric = BNSA(env=G, 
                                  static_nodes=existed_units,
                                  dynamic_nodes=new_units,
                                  area=points_mask,
                                  )


        assert best_metric <= 5.3

    def test_sa_cover_index(self, load_G):
        '''
        Тест SA. Метрика: ИП-5
        Только динамические узлы.
        '''
        G = load_G

        nodes = list(G.nodes())
        new_units = {nodes[3000]: 'c',
                    nodes[4000]: 'd'}

        BNSA = BestNodesSA(state_function=FirstArrivalUnitState(),
                            metric_function=CoverIndex(5),
                    end_temperature = 0.01,
                    )

        _, best_metric = BNSA(env=G,
                                  dynamic_nodes=new_units,
                                  )

        assert best_metric > 18

    def test_ga_many_units(self, load_G):
        '''
        Тест ГА для множества подразделений
        '''
        G = load_G
        nodes = list(G.nodes())
        new_units = {nodes[1000]:'a',
                    nodes[1500]:'b',
                    nodes[2000]:'c',
                    nodes[2500]:'d',
                    nodes[3000]:'e',
                    nodes[3500]:'f',
                    nodes[4000]:'g',}

        BNSA = BestNodesSA(state_function=FirstArrivalUnitState(),
                            metric_function=ArrivalTime(),
                            mutation_max_count=3,
                            end_temperature = 0.01,
                            )

        _, best_metric = BNSA(env=G,
                                  dynamic_nodes=new_units,
                                  )
        assert best_metric < 4.5