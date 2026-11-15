'''
Тесты drop_trash_points и BestNodesGAKopt

`pytest tests/test_lscp_mclp_extra.py -s`
'''

import pytest

from genesis.best_points import BestNodeHillClimbing
from genesis.lscp import drop_trash_points
from genesis.mclp import BestNodesKoptG, NodesMetric
from genesis.metrics import ArrivalTime, CoverIndex
from genesis.point_selectors import RandomNodesSelector
from genesis.states import FirstArrivalUnitState
from fire_units.mclp import BestNodesGAKopt


UNITS = {0: 'a', 7: 'b', 56: 'c', 63: 'd', 27: 'e', 28: 'f'}


@pytest.fixture
def state():
    return FirstArrivalUnitState()


def target(value_min):
    return lambda value, **kwargs: value >= value_min


class TestDropTrashPoints:
    @pytest.mark.parametrize('value_min', [20, 50])
    def test_target_kept(self, grid, state, value_min):
        '''
        После удаления метрика по-прежнему удовлетворяет цели, а лишние точки удалены
        '''
        left, value = drop_trash_points(env=grid, state_function=state, metric_function=CoverIndex(6),
                                        stop_case_function=target(value_min), dynamic_nodes=dict(UNITS))
        assert value >= value_min
        assert 0 < len(left) < len(UNITS)
        assert set(left.items()) <= set(UNITS.items())

    def test_metric_matches_result(self, grid, state):
        left, value = drop_trash_points(env=grid, state_function=state, metric_function=CoverIndex(6),
                                        stop_case_function=target(50), dynamic_nodes=dict(UNITS))
        assert value == pytest.approx(NodesMetric(state, CoverIndex(6))(grid, list(left)))

    def test_unreachable_target(self, grid, state):
        '''
        Если цель недостижима даже со всеми точками, ни одна точка не удаляется
        '''
        left, value = drop_trash_points(env=grid, state_function=state, metric_function=CoverIndex(6),
                                        stop_case_function=target(100), dynamic_nodes=dict(UNITS))
        assert left == UNITS
        assert value < 100

    def test_static_nodes_kept(self, grid, state):
        static = {36: 'S'}
        left, value = drop_trash_points(env=grid, state_function=state, metric_function=CoverIndex(6),
                                        stop_case_function=target(50), dynamic_nodes=dict(UNITS), static_nodes=static)
        assert 36 not in left
        assert value == pytest.approx(NodesMetric(state, CoverIndex(6))(grid, list(left) + [36]))

    def test_one_point_left(self, grid, state):
        left, _ = drop_trash_points(env=grid, state_function=state, metric_function=CoverIndex(6),
                                    stop_case_function=target(0), dynamic_nodes=dict(UNITS))
        assert len(left) == 1


class TestBestNodesGAKopt:
    @pytest.mark.parametrize('metric', [ArrivalTime(), CoverIndex(6)], ids=['ArrivalTime', 'CoverIndex'])
    def test_improves_and_keeps_units(self, grid, state, metric):
        start = {0: 'a', 7: 'b'}
        kopt = BestNodesKoptG(state, metric, BestNodeHillClimbing(state, metric), iterations=1)
        best_nodes, value = BestNodesGAKopt(state, metric, kopt, RandomNodesSelector(),
                                            population_size=6, epochs=3)(env=grid, dynamic_nodes=dict(start))

        start_value = NodesMetric(state, metric)(grid, list(start))
        assert sorted(best_nodes.values()) == ['a', 'b']
        assert metric.compare(start_value, value) == value
        assert value == pytest.approx(NodesMetric(state, metric)(grid, list(best_nodes)))
