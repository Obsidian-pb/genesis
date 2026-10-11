'''
Тесты алгоритмов поиска одного лучшего узла, ранее не покрытых тестами:
BestNodeBee, BestNodeSquareZoom, BestNodeCircleZoom, BestNodeGWO,
а также варианты скалолаза из fire_units

`pytest tests/test_point_algorithms.py -s`
'''

import pytest

import numpy as np
import pandas as pd

from genesis.best_points import (BestNodeBee, BestNodeCircleZoom, BestNodeGWO, BestNodeSquareZoom,
                                 BestNodesFull, NodeMetric)
from genesis.metrics import ArrivalTime, CoverIndex
from genesis.states import FirstArrivalUnitState
from fire_units.best_points import (BestNodeHillClimbing_HD_Max_Mean, BestNodeHillClimbing_HD_Max_Mean_Metric,
                                    BestNodeHillClimbing_maxMean_Metric, BestNodeHillClimbingHD)


CENTER = {27, 28, 35, 36}


@pytest.fixture
def state():
    return FirstArrivalUnitState()


@pytest.fixture(scope='module')
def left_half(grid):
    '''
    Область расчета - левая половина сетки. Оптимум: узлы 25, 26, 33, 34, среднее время 7 минут
    '''
    return pd.Series([n % 8 < 4 for n in grid.nodes()], index=list(grid.nodes()))


# Алгоритмы, которые на сетке 8x8 находят точный оптимум
EXACT_ALGORITHMS = [
    pytest.param(lambda st, m: BestNodeBee(st, m, scouts_count=10, best_scouts_count=3), id='Bee'),
    pytest.param(lambda st, m: BestNodeSquareZoom(st, m), id='SquareZoom'),
    pytest.param(lambda st, m: BestNodeCircleZoom(st, m), id='CircleZoom'),
]


class TestExactOnGrid:
    @pytest.mark.parametrize('make', EXACT_ALGORITHMS)
    @pytest.mark.parametrize('metric, optimum', [(ArrivalTime(), 9.0), (ArrivalTime(np.max), 17.0)])
    def test_arrival_time(self, grid, state, make, metric, optimum):
        node, value = make(state, metric)(env=grid)[:2]
        assert node in CENTER
        assert value == pytest.approx(optimum)

    @pytest.mark.parametrize('make', EXACT_ALGORITHMS)
    def test_cover_index(self, grid, state, make):
        '''
        Максимизируемая метрика: ИП-6 = 20.3125 % (13 узлов из 64) во внутреннем квадрате 4x4
        '''
        _, value = make(state, CoverIndex(6))(env=grid)[:2]
        assert value == pytest.approx(20.3125)

    @pytest.mark.parametrize('make', EXACT_ALGORITHMS)
    def test_area(self, grid, state, left_half, make):
        node, value = make(state, ArrivalTime())(env=grid, area=left_half)[:2]
        assert node in {25, 26, 33, 34}
        assert value == pytest.approx(7.0)

    @pytest.mark.parametrize('make', EXACT_ALGORITHMS)
    def test_metric_matches_node(self, grid, state, make):
        '''
        Возвращаемая метрика - метрика возвращаемого узла
        '''
        node, value = make(state, ArrivalTime())(env=grid)[:2]
        assert value == pytest.approx(NodeMetric(state, ArrivalTime())(env=grid, node=node))


class TestGWO:
    '''
    Стохастический алгоритм без гарантии оптимума: проверяется качество, а не точное значение
    '''
    @pytest.mark.parametrize('metric, optimum', [(ArrivalTime(), 9.0), (ArrivalTime(np.max), 17.0)])
    def test_close_to_optimum(self, grid, state, metric, optimum):
        node, value = BestNodeGWO(state, metric, max_iter=10, pack_size=6)(env=grid)
        assert value == pytest.approx(NodeMetric(state, metric)(env=grid, node=node))
        assert value <= optimum * 1.15

    def test_cover_index(self, grid, state):
        _, value = BestNodeGWO(state, CoverIndex(6), max_iter=10, pack_size=6)(env=grid)
        assert value == pytest.approx(20.3125)

    def test_too_few_candidates(self, grid, state):
        with pytest.raises(ValueError):
            BestNodeGWO(state, ArrivalTime())(env=grid, points_list={0, 1})


class TestPointsList:
    '''
    Ограничение кандидатов `points_list`: результат должен быть одним из кандидатов
    '''
    CANDIDATES = {0, 7, 56, 63, 9}

    @pytest.mark.parametrize('make', [
        pytest.param(lambda st: BestNodeSquareZoom(st, ArrivalTime()), id='SquareZoom'),
        pytest.param(lambda st: BestNodeCircleZoom(st, ArrivalTime()), id='CircleZoom'),
        pytest.param(lambda st: BestNodesFull(st, ArrivalTime()), id='Full'),
    ])
    def test_respected(self, grid, state, make):
        node, value = make(state)(env=grid, points_list=self.CANDIDATES)[:2]
        assert node == 9
        assert value == pytest.approx(12.0)

    @pytest.mark.xfail(strict=True, reason='Известная ошибка: поиск в окрестности лучших разведчиков '
                                           'вызывается без points_list и уходит за пределы списка')
    def test_bee(self, grid, state):
        node, _ = BestNodeBee(state, ArrivalTime(), scouts_count=10, best_scouts_count=3)(env=grid, points_list=self.CANDIDATES)
        assert node in self.CANDIDATES

    @pytest.mark.xfail(strict=True, reason='Известная ошибка: волки перемещаются по графу без учета points_list')
    def test_gwo(self, grid, state):
        node, _ = BestNodeGWO(state, ArrivalTime(), max_iter=10, pack_size=6)(env=grid, points_list=self.CANDIDATES)
        assert node in self.CANDIDATES


class TestFireUnitsHillClimbing:
    @pytest.mark.parametrize('cls', [BestNodeHillClimbing_HD_Max_Mean_Metric, BestNodeHillClimbing_maxMean_Metric,
                                     BestNodeHillClimbing_HD_Max_Mean, BestNodeHillClimbingHD])
    @pytest.mark.parametrize('start_point', [None, 0])
    def test_arrival_time(self, grid, state, cls, start_point):
        node, value = cls(state, ArrivalTime())(env=grid, start_point=start_point)
        assert node in CENTER
        assert value == pytest.approx(9.0)

    @pytest.mark.parametrize('cls', [BestNodeHillClimbing_HD_Max_Mean_Metric, BestNodeHillClimbing_maxMean_Metric,
                                     BestNodeHillClimbingHD])
    def test_cover_index(self, grid, state, cls):
        '''
        Последний этап этих вариантов идет по переданной метрике
        '''
        _, value = cls(state, CoverIndex(6))(env=grid)
        assert value == pytest.approx(20.3125)

    def test_hd_max_mean_ignores_metric(self, grid, state):
        '''
        BestNodeHillClimbing_HD_Max_Mean ищет по максимальному и среднему времени
        и возвращает среднее время, переданная метрика не используется
        '''
        _, value = BestNodeHillClimbing_HD_Max_Mean(state, CoverIndex(6))(env=grid)
        assert value == pytest.approx(9.0)
