'''
Тесты на ошибки, найденные при чтении кода (раздел 1.3 REDESIGN_GENESIS.MD)

`pytest tests/test_review_fixes.py -s`
'''

import pytest

import geopandas as gpd
import networkx as nx
import pandas as pd
from shapely.geometry import LineString

from genesis.best_points import BestNodeHillClimbing
from genesis.lscp import LSCP_ADD
from genesis.mclp import BestNodesGA, BestNodesKoptG
from genesis.metrics import ArrivalTime, CoverIndex
from genesis.point_selectors import RandomNodesSelector
from genesis.states import FirstArrivalUnitState
from genesis.tools import list_dict_concat
from graphs.algorithms import generate_grid_graph, graph_rise_from_gpkg


@pytest.fixture(scope='module')
def grid():
    '''
    Сетка 8x8, время проезда каждого ребра 2 минуты
    '''
    return generate_grid_graph(8, 8, step=1000, speed=30, add_geometry=False)


@pytest.fixture
def state():
    return FirstArrivalUnitState()


class TestRandomNodesSelector:
    def test_bad_nodes_list(self):
        '''
        Исключение при неверном `nodes_list` выбрасывается, а не только создается
        '''
        with pytest.raises(TypeError):
            RandomNodesSelector(nodes_list=5)

    def test_no_duplicates(self, grid):
        '''
        При k > 1 узлы выбираются без повторов
        '''
        nodes = RandomNodesSelector()(env=grid, points={}, k=60)
        assert len(set(nodes)) == 60


class TestLSCPAddNodesList:
    def test_matrix_not_truncated(self, grid, state):
        '''
        Вызов с `nodes_list` не обрезает матрицу объекта для следующих вызовов
        '''
        matrix = pd.DataFrame({n: pd.Series(nx.single_source_dijkstra_path_length(grid, n, weight='travel_time'))
                               for n in grid.nodes()})
        add = LSCP_ADD(state_function=state, matrix=matrix, metric_function=CoverIndex(6), ip_val=6,
                       stop_case_function=lambda value, **kwargs: value >= 100)
        best_nodes, _ = add(env=grid, nodes_list={0, 7, 56, 63, 27})

        assert set(best_nodes) <= {0, 7, 56, 63, 27}
        assert add.matrix.shape == (64, 64)

    def test_uncoverable_objects(self, grid, state):
        '''
        Если оставшиеся объекты не прикрываются ни одним допустимым узлом,
        расчет останавливается, а не зацикливается
        '''
        matrix = pd.DataFrame({n: pd.Series(nx.single_source_dijkstra_path_length(grid, n, weight='travel_time'))
                               for n in grid.nodes()})
        add = LSCP_ADD(state_function=state, matrix=matrix, metric_function=CoverIndex(6), ip_val=6)
        with pytest.warns(UserWarning, match='не могут быть прикрыты'):
            best_nodes, _ = add(env=grid, nodes_list={0})

        assert list(best_nodes) == [0]


class TestGAPopulationSize:
    def test_population_size_5(self, state):
        BestNodesGA(state, ArrivalTime(), RandomNodesSelector(), population_size=5)

    def test_population_size_0(self, state):
        with pytest.raises(ValueError):
            BestNodesGA(state, ArrivalTime(), RandomNodesSelector(), population_size=0)


class TestKoptGArea:
    def test_best_point_function_not_changed(self, grid, state):
        '''
        Расчет с `area` не меняет `appr_val` переданного алгоритма
        '''
        hill_climbing = BestNodeHillClimbing(state, ArrivalTime(), appr_val=0.95)
        area = pd.Series(True, index=list(grid.nodes()))
        kopt = BestNodesKoptG(state, ArrivalTime(), hill_climbing, iterations=1, appr_val_in_area=0.5)
        kopt(env=grid, dynamic_nodes={0: 'a', 63: 'b'}, area=area)

        assert hill_climbing.appr_val == 0.95


class TestListDictConcat:
    def test_error_message(self):
        with pytest.raises(TypeError, match='различный тип'):
            list_dict_concat([1], {2: 3})


class TestGraphRiseFromGpkg:
    def test_input_not_changed(self):
        '''
        Округление координат не меняет датафрейм вызывающей стороны.
        Без СК проецирование не выполняется, расчет шел по исходным данным
        и портил их до того, как функция падала на отсутствии СК
        '''
        roads = gpd.GeoDataFrame({'oneway': [False], 'reversed': [False]},
                                 geometry=[LineString([(0.4, 0.4), (10.6, 0.4)])])
        geometry = roads.geometry.copy()
        with pytest.raises(ValueError):
            graph_rise_from_gpkg(roads)

        assert roads.geometry.equals(geometry)


class TestFirstArrivalUnitCacheState:
    '''
    Расчет с кэшем статических подразделений совпадает с полным расчетом
    '''
    def test_fractional_times(self):
        '''
        На графе с дробными временами кэш давал завышенное время в части узлов:
        задержка из кэша не вычиталась перед сравнением с расстояниями алгоритма Дейкстры
        '''
        import osmnx as ox
        from genesis.states import FirstArrivalUnitCacheState

        G = ox.load_graphml('tests/data/test_rng.ml')
        nodes = list(G.nodes())
        static = {nodes[1]: 'A', nodes[len(nodes) // 3]: 'B'}
        dynamic = {nodes[len(nodes) // 2]: 'C', nodes[-2]: 'D'}
        state = FirstArrivalUnitState()
        times_cache, nearest_cache = state(env=G, points=static)

        times, _ = FirstArrivalUnitCacheState(times_cache=times_cache,
                                              nearest_cache=nearest_cache)(env=G, points=dynamic)
        times_full, _ = state(env=G, points={**static, **dynamic})

        pd.testing.assert_series_equal(times.sort_index(), times_full.sort_index(), check_names=False)

    def test_without_cache(self, grid):
        from genesis.states import FirstArrivalUnitCacheState

        times, nearest = FirstArrivalUnitCacheState()(env=grid, points={0: 'A'})
        times_plain, nearest_plain = FirstArrivalUnitState()(env=grid, points={0: 'A'})

        pd.testing.assert_series_equal(times.sort_index(), times_plain.sort_index(), check_names=False)
        assert (nearest == 'A').all()

    def test_area(self, grid):
        from genesis.states import FirstArrivalUnitCacheState

        state = FirstArrivalUnitState()
        times_cache, nearest_cache = state(env=grid, points={0: 'A'})
        area = pd.Series([n < 32 for n in grid.nodes()], index=list(grid.nodes()))
        times, nearest = FirstArrivalUnitCacheState(times_cache=times_cache,
                                                    nearest_cache=nearest_cache)(env=grid, points={63: 'B'}, area=area)
        assert set(times.index) == set(range(32))
        assert set(nearest.index) == set(range(32))


class TestMonkeyPointsListSet:
    def test_set(self, grid, state):
        from genesis.best_points import BestNodeMonkey

        node, _ = BestNodeMonkey(state, ArrivalTime())(env=grid, points_list={0, 7, 56, 63, 9})
        assert node in grid.nodes()


class TestKmhToMmNumpy:
    def test_numpy_number(self):
        import numpy as np
        from graphs.speeds import kmh_to_mm

        assert kmh_to_mm(np.int64(60)) == 1000.0
        assert kmh_to_mm(np.float64(30)) == 500.0
