"""Проверки прозрачного движка без genesis.fast и решателей Certus."""

import networkx as nx
import numpy as np
import pandas as pd
import pytest

pytest.importorskip('scipy')

from genesis import engine
from genesis.backends import use_backend
from genesis.metrics import ArrivalTime, CoverIndex, CoverIndexValue
from genesis.states import FirstArrivalUnitState, get_atm
from graphs.speeds import kmh_to_mm, set_graph_travel_times


@pytest.fixture(autouse=True)
def clear_engine():
    engine.clear()
    with use_backend('scipy'):
        yield
    engine.clear()


def reference_algorithm(**kwargs):
    """Обёртка намеренно отключает быстрый путь состояния."""
    return nx.multi_source_dijkstra(**kwargs)


@pytest.fixture
def directed():
    G = nx.MultiDiGraph()
    G.add_nodes_from(range(6))
    G.add_edge(0, 1, travel_time=4.0)
    G.add_edge(0, 1, travel_time=0.75)
    G.add_edge(1, 2, travel_time=0.0)
    G.add_edge(2, 3, travel_time=1.5)
    G.add_edge(4, 3, travel_time=0.5)
    return G


@pytest.mark.parametrize('points', [[0], [0, 4], {0: 'A', 4: 'B'}])
@pytest.mark.parametrize('cutoff', [None, 0.0, 1.0, 3.0])
def test_state_matches_networkx(directed, points, cutoff):
    fast = FirstArrivalUnitState(delay=0.3)
    slow = FirstArrivalUnitState(state_algorithm=reference_algorithm, delay=0.3)
    times, nearest = fast(env=directed, points=points, cutoff=cutoff)
    expected_times, expected_nearest = slow(env=directed, points=points, cutoff=cutoff)
    pd.testing.assert_series_equal(times.sort_index(), expected_times.sort_index(), check_names=False)
    pd.testing.assert_series_equal(nearest.sort_index(), expected_nearest.sort_index(), check_names=False)


def test_state_ties_are_valid():
    G = nx.DiGraph()
    G.add_weighted_edges_from([(0, 2, 1), (1, 2, 1)], weight='travel_time')
    times, nearest = FirstArrivalUnitState(delay=0)(env=G, points=[0, 1])
    assert times[2] == 1
    assert nearest[2] in (0, 1)


def test_undirected_and_default_weight():
    G = nx.Graph()
    G.add_edge(0, 1)
    G.add_edge(1, 2, travel_time=2.0)
    times, _ = FirstArrivalUnitState(delay=0)(env=G, points=[2])
    assert times.to_dict() == {0: 3.0, 1: 2.0, 2: 0.0}


def test_state_callable_weight_and_custom_algorithm(directed):
    calls = []

    def algorithm(**kwargs):
        calls.append(kwargs)
        return nx.multi_source_dijkstra(**kwargs)

    weight = lambda u, v, edges: min(d['travel_time'] for d in edges.values())
    state = FirstArrivalUnitState(state_algorithm=algorithm, weight=weight, delay=0)
    times, _ = state(env=directed, points=[0])
    assert len(calls) == 1
    assert times[3] == pytest.approx(2.25)
    assert engine.evaluate(state, CoverIndex(2), directed, [0]) is None


def test_cache_reuse_and_explicit_clear(directed):
    first = engine.graph_index(directed)
    assert engine.graph_index(directed) is first
    directed[0][1][1]['travel_time'] = 8.0
    engine.clear(directed)
    second = engine.graph_index(directed)
    assert second is not first
    assert engine.distance_rows(second, second.positions([0]))[0, second.index[1]] == 4.0


def test_cache_topology_changes(directed, monkeypatch):
    monkeypatch.setattr(engine, 'EDGES_CHECK_SECONDS', 0)
    first = engine.graph_index(directed)
    directed.add_edge(3, 5, travel_time=1.0)
    second = engine.graph_index(directed)
    assert second is not first
    directed.add_node(6)
    assert engine.graph_index(directed) is not second


def test_speed_update_invalidates_cache():
    G = nx.MultiDiGraph()
    G.add_edge(0, 1, highway='residential', length=1000.0)
    set_graph_travel_times(G, [30] * 5, kmh_to_mm)
    first = engine.graph_index(G)
    set_graph_travel_times(G, [60] * 5, kmh_to_mm)
    second = engine.graph_index(G)
    assert second is not first
    assert second.adjacency[0, 1] == pytest.approx(first.adjacency[0, 1] / 2)


def test_subgraph_paths_stay_inside_zone():
    G = nx.DiGraph()
    G.add_weighted_edges_from([(0, 1, 1), (1, 2, 1), (0, 2, 10)], weight='travel_time')
    engine.graph_index(G)
    zone = G.subgraph([0, 2])
    times, _ = FirstArrivalUnitState(delay=0)(env=zone, points=[0])
    assert times[2] == 10


@pytest.mark.parametrize('metric', [ArrivalTime(), ArrivalTime(np.max), CoverIndex(2)])
def test_native_metric_and_area_match_old_interface(directed, metric):
    area = pd.Series({n: n != 1 for n in directed})
    state = FirstArrivalUnitState(delay=0.3)
    slow = FirstArrivalUnitState(state_algorithm=reference_algorithm, delay=0.3)
    times, _ = slow(env=directed, points=[0, 4], area=area)
    count, value = engine.evaluate(state, metric, directed, [0, 4], area)
    assert count == len(times)
    assert value == pytest.approx(metric(times))


def test_native_cover_index_value(directed):
    data = pd.DataFrame({'node': [0, 1, 1, 3, 5], 'value': [1, 3, 4, 2, 9]})
    metric = CoverIndexValue(data, value_field='value', ip_val=2)
    state = FirstArrivalUnitState()
    times, _ = state(env=directed, points=[0])
    _, value = engine.evaluate(state, metric, directed, [0])
    assert value == pytest.approx(metric(times))


def test_custom_metric_falls_back(directed):
    metric = ArrivalTime(lambda times: times.iloc[0])
    assert engine.evaluate(FirstArrivalUnitState(), metric, directed, [0]) is None


@pytest.mark.parametrize('per_record_limit', [False, True])
def test_get_atm_matches_networkx(directed, per_record_limit):
    data = pd.DataFrame({'node': [3, 2, 3, 5], 'limit': [2, 0, 4, 0]},
                        index=['a', 'b', 'c', 'd'])
    options = dict(data=data, delay=0.25, cutoff=3, target_set={0, 1, 2, 4, 5},
                   batch_size=2, print_calc_states=False)
    if per_record_limit:
        options['data_cutoff_field'] = 'limit'
    fast = get_atm(directed, **options)
    # Callable-версия использует сохранённую реализацию get_atm через networkx.
    weight = lambda u, v, edges: min(d['travel_time'] for d in edges.values())
    slow = get_atm(directed, weight=weight, **options)
    pd.testing.assert_frame_equal(fast.sort_index().sort_index(axis=1),
                                  slow.sort_index().sort_index(axis=1), check_dtype=False)


def test_sparse_arrival_keeps_zero_and_direction(directed):
    index = engine.graph_index(directed)
    distances = engine.arrival_distances(index, index.positions([2]), limits=np.array([0.0]), batch_size=1)
    row = distances.getrow(0)
    assert set(index.nodes[row.indices]) == {1, 2}
    assert np.all(row.data == 0)


def test_distance_rows_reuse_and_eviction(directed, monkeypatch):
    index = engine.graph_index(directed)
    positions = index.positions([0, 4])
    rows = engine.distance_rows(index, positions)
    np.testing.assert_array_equal(rows, engine.distance_rows(index, positions))
    monkeypatch.setattr(engine, 'ROWS_CACHE_BYTES', 1)
    other = engine.distance_rows(index, index.positions([1]))
    assert len(index._rows) == 1
    assert other[0, index.index[2]] == 0


def test_graph_index_supports_tuple_nodes():
    G = nx.Graph()
    G.add_edge((0, 0), (1, 0), travel_time=2)
    index = engine.graph_index(G)
    assert index.nodes.shape == (2,)
    assert index.positions([(1, 0)]).tolist() == [1]
