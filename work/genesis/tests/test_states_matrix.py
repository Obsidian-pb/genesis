'''
Тесты состояний по матрице прибытия и с кэшем, функции get_atm

`pytest tests/test_states_matrix.py -s`
'''

import pytest

import numpy as np
import pandas as pd

from genesis._errors import KeyNotInMatrixError
from genesis.states import ArrivalTimeMatrixState, FirstArrivalUnitCacheState, FirstArrivalUnitState, get_atm
from genesis.swiss_knife import DELAY_TIME


UNITS = {0: 'A', 63: 'B'}


@pytest.fixture(scope='module')
def matrix(grid):
    return get_atm(grid, print_calc_states=False)


def unambiguous(times_a, times_b):
    '''
    Узлы, в которые подразделения прибывают за разное время: ближайшее подразделение определено однозначно
    '''
    return times_a.index[(times_a - times_b.reindex(times_a.index)).abs() > 1e-9]


class TestGetAtm:
    def test_all_nodes(self, grid, matrix):
        assert matrix.shape == (64, 64)
        assert set(matrix.index) == set(grid.nodes())

    def test_delay_included(self, matrix):
        '''
        Время прибытия из узла в него же - задержка DELAY_TIME
        '''
        assert matrix.loc[27, 27] == pytest.approx(DELAY_TIME)
        assert matrix.loc[0, 1] == pytest.approx(DELAY_TIME + 2)

    def test_rows_are_data_index(self, grid):
        '''
        Строки матрицы - индексы записей data, а не номера узлов (контракт, Н2)
        '''
        data = pd.DataFrame({'node': [0, 0, 27]}, index=['b1', 'b2', 'b3'])
        m = get_atm(grid, data=data, print_calc_states=False)
        assert list(m.index) == ['b1', 'b2', 'b3']
        assert m.loc['b3', 27] == pytest.approx(DELAY_TIME)

    def test_cutoff(self, grid):
        m = get_atm(grid, cutoff=7, print_calc_states=False)
        assert np.nanmax(m.values) <= 7

    def test_sample_size(self, grid):
        m = get_atm(grid, data_sample_size=10, print_calc_states=False)
        assert len(m) == 10


class TestArrivalTimeMatrixState:
    def test_same_as_graph(self, grid, matrix):
        '''
        По полной матрице времена и ближайшие подразделения совпадают с расчетом по графу
        '''
        times, nearest = ArrivalTimeMatrixState(matrix)(env=grid, points=UNITS)
        times_g, nearest_g = FirstArrivalUnitState()(env=grid, points=UNITS)

        pd.testing.assert_series_equal(times.sort_index(), times_g.sort_index(), check_names=False, check_dtype=False)
        assert (nearest.sort_index() == nearest_g.sort_index()).all()

    def test_list_points(self, grid, matrix):
        times, nearest = ArrivalTimeMatrixState(matrix)(env=grid, points=[0, 63])
        assert len(times) == 64
        assert set(nearest) == {'0', '63'}

    def test_area(self, grid, matrix):
        area = pd.Series([n < 32 for n in grid.nodes()], index=list(grid.nodes()))
        times, nearest = ArrivalTimeMatrixState(matrix)(env=grid, points=UNITS, area=area)
        assert set(times.index) == set(range(32))
        assert set(nearest.index) == set(range(32))

    def test_missing_node(self, grid, matrix):
        with pytest.raises(KeyNotInMatrixError):
            ArrivalTimeMatrixState(matrix[[0, 1]])(env=grid, points=UNITS)

    def test_duplicate_points(self, grid, matrix):
        with pytest.raises(ValueError):
            ArrivalTimeMatrixState(matrix)(env=grid, points=[0, 0])


class TestFirstArrivalUnitCacheState:
    '''
    Кэш - состояние статических подразделений; при вызове рассчитываются только новые
    '''
    @pytest.mark.parametrize('dynamic', [{63: 'B'}, {36: 'B'}, {7: 'B', 56: 'C'}])
    def test_same_as_full_calculation(self, grid, dynamic):
        state = FirstArrivalUnitState()
        static = {0: 'A'}
        times_cache, nearest_cache = state(env=grid, points=static)

        times, nearest = FirstArrivalUnitCacheState(times_cache=times_cache,
                                                    nearest_cache=nearest_cache)(env=grid, points=dynamic)
        times_full, nearest_full = state(env=grid, points={**static, **dynamic})

        pd.testing.assert_series_equal(times.sort_index(), times_full.sort_index(), check_names=False, check_dtype=False)
        # При равном времени прибытия выбор подразделения произволен - сравниваются только однозначные узлы
        nodes = unambiguous(times_cache, state(env=grid, points=dynamic)[0])
        assert (nearest[nodes] == nearest_full[nodes]).all()
