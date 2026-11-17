'''
Тесты метрик по зданиям и с весами, состояния FireDemandSatisfyState

`pytest tests/test_metrics_buildings.py -s`
'''

import pytest

import numpy as np
import pandas as pd

from genesis.metrics import ArrivalTime, CoverIndex, CoverIndexValue
from genesis.states import FirstArrivalUnitState
from fire_units.metrics import ArrivalTimeBuilding, CoverIndexBuilding, CoverIndexBuildingADD
from fire_units.states import FireDemandSatisfyState


@pytest.fixture(scope='module')
def times(grid):
    '''
    Время прибытия одного подразделения из угла сетки
    '''
    return FirstArrivalUnitState()(env=grid, points={0: 'A'})[0]


@pytest.fixture(scope='module')
def building_times(grid_buildings, times):
    return grid_buildings['node'].map(times)


@pytest.fixture(scope='module')
def left_half(grid):
    return pd.Series([n % 8 < 4 for n in grid.nodes()], index=list(grid.nodes()))


class TestBuildingMetrics:
    '''
    Значения метрик сравниваются с расчетом вручную по каждому зданию
    '''
    def test_cover_index_building(self, grid_buildings, times, building_times):
        assert CoverIndexBuilding(grid_buildings, ip_val=10)(times) == pytest.approx(100 * (building_times <= 10).mean())

    def test_cover_index_building_add(self, grid_buildings, times, building_times):
        assert CoverIndexBuildingADD(grid_buildings, ip_val=10)(times) == pytest.approx(100 * (building_times <= 10).mean())

    @pytest.mark.parametrize('f', [np.mean, np.max])
    def test_arrival_time_building(self, grid_buildings, times, building_times, f):
        assert ArrivalTimeBuilding(grid_buildings, f=f)(times) == pytest.approx(f(building_times))

    def test_cover_index_value(self, grid_buildings, times, building_times):
        pop = grid_buildings['pop']
        expected = 100 * pop[building_times <= 10].sum() / pop.sum()
        assert CoverIndexValue(grid_buildings, value_field='pop', ip_val=10)(times) == pytest.approx(expected)

    def test_buildings_differ_from_nodes(self, grid_buildings, times):
        '''
        Несколько зданий на узле меняют значение по сравнению с метрикой по узлам
        '''
        assert CoverIndexBuilding(grid_buildings, ip_val=10)(times) != pytest.approx(CoverIndex(10)(times))

    def test_missing_node_field(self, grid_buildings):
        with pytest.raises(KeyError):
            CoverIndexBuilding(grid_buildings.rename(columns={'node': 'n'}))

    def test_missing_value_field(self, grid_buildings):
        with pytest.raises(KeyError):
            CoverIndexValue(grid_buildings, value_field='population')


class TestArea:
    def test_cover_index(self, times, left_half):
        assert CoverIndex(10)(times, area=left_half) == pytest.approx(100 * (times[left_half] <= 10).mean())

    def test_arrival_time(self, times, left_half):
        assert ArrivalTime()(times, area=left_half) == pytest.approx(times[left_half].mean())

    def test_cover_index_building(self, grid_buildings, times, building_times, left_half):
        in_area = grid_buildings['node'].map(left_half)
        expected = 100 * (building_times[in_area] <= 10).mean()
        assert CoverIndexBuilding(grid_buildings, ip_val=10)(times, area=left_half) == pytest.approx(expected)

    def test_cover_index_value(self, grid_buildings, times, building_times, left_half):
        in_area = grid_buildings['node'].map(left_half)
        pop = grid_buildings['pop']
        expected = 100 * pop[in_area & (building_times <= 10)].sum() / pop[in_area].sum()
        assert CoverIndexValue(grid_buildings, value_field='pop', ip_val=10)(times, area=left_half) == pytest.approx(expected)


class TestEmptyState:
    @pytest.mark.parametrize('make, zero_val', [
        pytest.param(lambda b: CoverIndex(10), 0, id='CoverIndex'),
        pytest.param(lambda b: ArrivalTime(), 0, id='ArrivalTime'),
        pytest.param(lambda b: ArrivalTimeBuilding(b), 1000, id='ArrivalTimeBuilding'),
        pytest.param(lambda b: CoverIndexBuilding(b), 0, id='CoverIndexBuilding'),
    ])
    def test_zero_val(self, grid_buildings, make, zero_val):
        assert make(grid_buildings)(pd.Series([], dtype=float, name='times')) == zero_val

    def test_wrong_type(self):
        with pytest.raises(TypeError):
            CoverIndex(10)(np.array([1.0, 2.0]))


class TestFireDemandSatisfyState:
    def test_demand_over_time(self, grid, grid_buildings, times):
        demand, nearest = FireDemandSatisfyState()(env=grid, points={0: 'A'}, buildings=grid_buildings)
        expected = grid_buildings['demand'] / grid_buildings['node'].map(times)

        assert len(demand) == len(grid_buildings)
        assert np.allclose(demand.sort_index(), expected.sort_index())
        assert set(nearest) == {'A'}
