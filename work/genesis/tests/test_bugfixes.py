'''
Тесты на исправленные ошибки в алгоритмах (№ 1–7 из REDESIGN_GENESIS.MD)

`pytest tests/test_bugfixes.py -s`
'''

import random

import pytest

import networkx as nx
import pandas as pd

from genesis.best_points import BestNodeHillClimbing, BestNodeHillClimbing_maxMean, BestNodesFull
from genesis.hybridisation import Hybridization
from genesis.lscp import LSCP_ADD
from genesis.mclp import BestNodesGA, BestNodesKoptG, BestNodesSA
from genesis.metrics import ArrivalTime, CoverIndex
from genesis.point_selectors import RandomNodesSelector
from genesis.states import FirstArrivalUnitState
from genesis.tools import ga_crossover, normalize_weights
from graphs.algorithms import generate_grid_graph


@pytest.fixture(scope='module')
def grid():
    '''
    Сетка 8x8, время проезда каждого ребра 2 минуты
    '''
    return generate_grid_graph(8, 8, step=1000, speed=30, add_geometry=False)


@pytest.fixture
def state():
    return FirstArrivalUnitState()


@pytest.fixture
def seed():
    '''
    Фиксирует `random` на время теста и восстанавливает состояние после,
    чтобы не влиять на остальные тесты
    '''
    random_state = random.getstate()
    yield random.seed
    random.setstate(random_state)


class TestSAMaximization:
    '''
    № 1. Отжиг при максимизируемой метрике
    '''
    def test_probability_for_maximization(self, state):
        sa = BestNodesSA(state, CoverIndex(5), RandomNodesSelector())
        # ИП 80 % -> 50 %: ухудшение на 30 пунктов
        assert sa._get_transition_probability(50 - 80, 0.5) == sa._get_transition_probability(80 - 50, 0.5)
        assert sa._get_transition_probability(50 - 80, 0.5) < 1

    def test_transition_probability_not_above_one(self, grid, state, monkeypatch, seed):
        probabilities = []

        def is_transition(self, probability):
            probabilities.append(probability)
            return random.random() <= probability

        monkeypatch.setattr(BestNodesSA, '_is_transition', is_transition)
        seed(1)
        sa = BestNodesSA(state, CoverIndex(5), RandomNodesSelector(), turns=200)
        sa(env=grid, dynamic_nodes={0: 'a', 63: 'b'})

        assert probabilities
        assert max(probabilities) <= 1


class TestGASelection:
    '''
    № 2. Одинаковая приспособленность всей популяции
    '''
    def test_equal_weights(self):
        assert list(normalize_weights([3.0, 3.0, 3.0])) == [1.0, 1.0, 1.0]
        assert list(normalize_weights([1.0, 2.0, 3.0])) == [0.0, 0.5, 1.0]

    def test_ga_without_mutation(self, grid, state):
        ga = BestNodesGA(state, ArrivalTime(), RandomNodesSelector(), population_size=8, epochs=5, mutation_rate=0)
        best_nodes, _ = ga(env=grid, dynamic_nodes={0: 'a', 1: 'b'})
        assert sorted(best_nodes.values()) == ['a', 'b']


class TestGACrossover:
    '''
    № 3. Потеря подразделений при скрещивании
    '''
    def test_node_collision(self):
        # Узел 5 у первого родителя занят подразделением 'a', у второго - 'b'
        child = ga_crossover({5: 'a', 6: 'b'}, {7: 'a', 5: 'b'})
        assert sorted(child.values()) == ['a', 'b']
        assert child[5] == 'a'

    def test_all_units_kept(self, grid, state, seed):
        sizes = set()
        ga = BestNodesGA(state, ArrivalTime(), RandomNodesSelector(), population_size=12, epochs=25)
        fit = ga._fit_function

        def fit_function(env, nodes, area=None, **kwargs):
            sizes.add(len(nodes))
            return fit(env, nodes, area, **kwargs)

        ga._fit_function = fit_function
        seed(3)
        best_nodes, _ = ga(env=grid, dynamic_nodes={0: 'a', 1: 'b', 2: 'c', 3: 'd'})

        assert sizes == {4}
        assert sorted(best_nodes.values()) == ['a', 'b', 'c', 'd']


class TestHybridizationArea:
    '''
    № 4. Hybridization с областью расчета
    '''
    def test_call_with_area(self, grid, state):
        area = pd.Series(True, index=list(grid.nodes()))
        kopt = BestNodesKoptG(state, ArrivalTime(), BestNodeHillClimbing(state, ArrivalTime()), iterations=2)
        best_nodes, _ = Hybridization(state, ArrivalTime(), [kopt])(env=grid, dynamic_nodes={0: 'a', 1: 'b'}, area=area)
        assert sorted(best_nodes.values()) == ['a', 'b']


class TestLSCPAddWithoutStopCase:
    '''
    № 5. LSCP_ADD без критерия остановки, но со статическими узлами
    '''
    def test_static_nodes(self, grid, state):
        matrix = pd.DataFrame({n: pd.Series(nx.single_source_dijkstra_path_length(grid, n, weight='travel_time'))
                               for n in grid.nodes()})
        add = LSCP_ADD(state_function=state, matrix=matrix, metric_function=CoverIndex(6), ip_val=6)
        add(env=grid, static_nodes={0: 'ПСЧ-1'})


class TestHillClimbingMaxMean:
    '''
    № 6. Второй этап стартует из результата первого, `all_neighbors` передается этапам
    '''
    def test_stages(self, grid, state, monkeypatch):
        calls = []

        def hill_climbing(self, env, start_point=None, **kwargs):
            calls.append((start_point, self.all_neighbors))
            return 10 + len(calls), 0

        monkeypatch.setattr(BestNodeHillClimbing, '__call__', hill_climbing)
        BestNodeHillClimbing_maxMean(state, all_neighbors=False)(env=grid, start_point=0)

        assert calls == [(0, False), (11, False)]


class TestFullSearchZeroMetric:
    '''
    № 7. Полный перебор, когда метрика во всех узлах равна 0
    '''
    def test_zero_metric(self, grid, state):
        node, metric = BestNodesFull(state, CoverIndex(0.5))(env=grid)
        assert node in grid.nodes()
        assert metric == 0


class TestMisnamedArguments:
    '''
    Н5. Аргумент с ошибочным именем не уходит молча в **kwargs
    '''
    def test_nodes_list_in_call(self, grid, state):
        with pytest.raises(TypeError, match='points_list'):
            BestNodesFull(state, ArrivalTime())(env=grid, nodes_list={0, 7, 56})

    def test_all_nodes_in_init(self, state):
        with pytest.raises(TypeError, match='all_neighbors'):
            BestNodeHillClimbing(state, ArrivalTime(), all_nodes=False)

    def test_points_list(self, grid, state):
        node, _ = BestNodesFull(state, ArrivalTime())(env=grid, points_list={0, 7, 56})
        assert node in {0, 7, 56}
