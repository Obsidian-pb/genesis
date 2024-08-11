'''
Тесты функций из модуля graphs
'''

import pytest

import osmnx as ox

from fire_units.settings import DEFAULT_SPEEDS
from graphs.speeds import kmh_to_mm, set_graph_travel_times




@pytest.fixture(scope='module')
def load_G():
    return ox.load_graphml("tests/data/test_rng.ml")


@pytest.fixture(scope='module')
def load_G_simplyfied():
    G = ox.load_graphml("tests/data/test_rng.ml")
    return ox.simplify_graph(G)


class TestKMHtoMM:
    def test_kmh_to_mm(self):
        '''
        Тест функции `kmh_to_mm`:

        Перевод км/ч в м/мин
        '''
        a = 30
        b = kmh_to_mm(a)
        assert b == 500

    # @pytest.mark.xfail()
    def test_kmh_to_mm_str(self):
        '''
        Тест функции `kmh_to_mm`:

        Передача скорости в неверном формате
        '''
        a = '30'
        with pytest.raises(TypeError):
            b = kmh_to_mm(a)

    def test_kmh_to_mm_prec(self):
        '''
        Тест функции `kmh_to_mm`:

        Проверка корректности округления до 2 знаков
        '''
        a = 40
        b = kmh_to_mm(a, precision=2)
        assert b == 666.67

class TestSetGraphTimes:
    '''
    Тесты для функции установки значений времени следования
    '''
    def test_set_graph_travel_times(self, load_G):
        '''
        Базовый тест
        '''
        G = load_G
        speeds = [kmh_to_mm(s) for s in DEFAULT_SPEEDS]

        edges_before = G.number_of_edges()
        set_graph_travel_times(G, speeds)
        edges_after = G.number_of_edges()

        assert edges_before == edges_after
        edges = ox.graph_to_gdfs(G, nodes=False, node_geometry=False)
        assert 'travel_time' in list(edges.columns)
        assert edges.maxspeed.min() == speeds[-1]
        assert edges.maxspeed.max() == speeds[1]
        assert edges['travel_time'].mean() == 0.22407020395479973

    def test_set_graph_travel_times_simple(self, load_G_simplyfied):
        '''
        Тест на упрощенном графе и со скоростями по умолчанию
        '''
        G = load_G_simplyfied
        set_graph_travel_times(G, DEFAULT_SPEEDS)

        edges = ox.graph_to_gdfs(G, nodes=False, node_geometry=False)
        assert 'travel_time' in list(edges.columns)
        assert edges.maxspeed.min() == DEFAULT_SPEEDS[-1]
        assert edges.maxspeed.max() == DEFAULT_SPEEDS[1]

    def test_set_graph_travel_times_simple2(self, load_G_simplyfied):
        '''
        Тест на упрощенном графе и со скоростями по умолчанию
        '''
        G = load_G_simplyfied
        set_graph_travel_times(G, DEFAULT_SPEEDS, kmh_to_mm, 'time', 'speed')

        edges = ox.graph_to_gdfs(G, nodes=False, node_geometry=False)
        assert 'time' in list(edges.columns)
        assert 'speed' in list(edges.columns)
        assert edges.speed.min() == [kmh_to_mm(s) for s in DEFAULT_SPEEDS][-1]
        assert edges.speed.max() == [kmh_to_mm(s) for s in DEFAULT_SPEEDS][1]
