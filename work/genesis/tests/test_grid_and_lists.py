'''
Тесты генератора сеток, перевода скорости и справочников lists

`pytest tests/test_grid_and_lists.py -s`
'''

import pytest

import networkx as nx

import lists
from graphs.algorithms import generate_grid_graph, remove_random_elements
from graphs.speeds import kmh_to_mm


class TestGenerateGridGraph:
    @pytest.mark.parametrize('n, m', [(3, 4), (8, 8)])
    def test_size(self, n, m):
        G = generate_grid_graph(n, m, step=1000, speed=30, add_geometry=False)
        # Ребра в обе стороны между соседями по горизонтали и вертикали
        assert G.number_of_nodes() == n * m
        assert G.number_of_edges() == 2 * ((n - 1) * m + n * (m - 1))

    def test_edges(self):
        G = generate_grid_graph(3, 4, step=1000, speed=30, add_geometry=False)
        for u, v, d in G.edges(data=True):
            assert d['length'] == pytest.approx(1000)
            assert d['travel_time'] == pytest.approx(1000 / kmh_to_mm(30))
            assert G.has_edge(v, u)
        assert nx.is_strongly_connected(G)

    def test_diagonals(self):
        G = generate_grid_graph(3, 4, step=1000, speed=30, add_geometry=False, diagonals=True)
        lengths = {round(d['length'], 1) for *_, d in G.edges(data=True)}
        assert lengths == {1000, 1414.2}
        assert max(dict(G.out_degree()).values()) == 8

    def test_geometry(self):
        G = generate_grid_graph(3, 3, step=1000, speed=30, add_geometry=True)
        assert all(d.get('geometry') is not None for *_, d in G.edges(data=True))

    def test_speed_distribution(self):
        G = generate_grid_graph(4, 4, step=1000, speed=((30, 60), (0.5, 0.5)), add_geometry=False)
        for *_, d in G.edges(data=True):
            assert d['speed_kph'] in (30, 60)
            assert d['travel_time'] == pytest.approx(1000 / kmh_to_mm(int(d['speed_kph'])))

    def test_bad_probabilities(self):
        with pytest.raises(ValueError):
            generate_grid_graph(3, 3, speed=((30, 60), (0.5, 0.6)))


class TestRemoveRandomElements:
    def test_counts(self):
        G = generate_grid_graph(8, 8, step=1000, speed=30, add_geometry=False)
        G2 = remove_random_elements(G, remove_nodes=5, remove_edges=10, seed=1)
        assert G2.number_of_nodes() == 59
        assert G.number_of_nodes() == 64

    def test_seed(self):
        G = generate_grid_graph(8, 8, step=1000, speed=30, add_geometry=False)
        a = remove_random_elements(G, remove_nodes=5, seed=1)
        b = remove_random_elements(G, remove_nodes=5, seed=1)
        assert set(a.nodes()) == set(b.nodes())


class TestKmhToMm:
    @pytest.mark.parametrize('kmh, mm', [(60, 1000.0), (30, 500.0), (0, 0.0)])
    def test_values(self, kmh, mm):
        assert kmh_to_mm(kmh) == mm

    def test_type(self):
        with pytest.raises(TypeError):
            kmh_to_mm('60')


class TestLists:
    def test_every_building_class_has_kfpo(self):
        '''
        Для каждого класса функциональной пожарной опасности здания есть параметры КФПО
        '''
        assert set(lists.BUILDINGS_KFPO.values()) <= set(lists.KFPO)

    def test_derived_dicts(self):
        assert len(lists.BUILDINGS_CLASS) == len(lists.BUILDINGS)
        assert set(lists.KFPO_DEMAND) == set(lists.KFPO)
