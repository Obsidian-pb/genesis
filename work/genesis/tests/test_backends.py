"""Безопасное включение ускорения: выбор режима не меняет старые вызовы."""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import os
import subprocess
import sys
import textwrap

import networkx as nx
import numpy as np
import pandas as pd
import pytest

from genesis import backends
from genesis.backends import get_backend, use_backend
from genesis.best_points import BestNodeGWO, NodeMetric
from genesis.mclp import BestNodesGA, BestNodesKoptG, BestNodesSA, NodesMetric
from genesis.metrics import ArrivalTime, CoverIndex
from genesis.point_selectors import RandomNodesSelector
from genesis.states import FirstArrivalUnitState, get_atm
from fire_units.mclp import BestNodesGAKopt


@pytest.fixture(autouse=True)
def legacy_context():
    # Эти проверки не зависят от --backend всего набора.
    with use_backend('networkx'):
        yield


def require_scipy():
    pytest.importorskip('scipy')


def test_nested_context_and_exception_restore():
    require_scipy()
    assert get_backend() == 'networkx'
    with use_backend('scipy'):
        assert get_backend() == 'scipy'
        with use_backend('networkx'):
            assert get_backend() == 'networkx'
        assert get_backend() == 'scipy'
        with pytest.raises(RuntimeError):
            with use_backend('networkx'):
                raise RuntimeError('test')
        assert get_backend() == 'scipy'
    assert get_backend() == 'networkx'
    with pytest.raises(RuntimeError):
        with use_backend('scipy'):
            raise RuntimeError('test')
    assert get_backend() == 'networkx'


@pytest.mark.parametrize('name', ['auto', 'SCIPY', '', None, 1])
def test_invalid_backend_does_not_change_context(name):
    with pytest.raises(ValueError, match='backend'):
        with use_backend(name):
            pytest.fail('invalid context entered')
    assert get_backend() == 'networkx'


def test_threads_do_not_share_backend():
    require_scipy()
    with use_backend('scipy'):
        with ThreadPoolExecutor(max_workers=1) as pool:
            assert pool.submit(get_backend).result(timeout=10) == 'networkx'
        assert get_backend() == 'scipy'
    assert get_backend() == 'networkx'


def test_async_tasks_have_independent_contexts():
    require_scipy()

    async def worker(name):
        with use_backend(name):
            await asyncio.sleep(0)
            return get_backend()

    async def run():
        assert await asyncio.gather(worker('scipy'), worker('networkx')) == ['scipy', 'networkx']
        assert get_backend() == 'networkx'
        with use_backend('scipy'):
            assert await asyncio.create_task(asyncio.to_thread(get_backend)) == 'scipy'

    asyncio.run(run())
    assert get_backend() == 'networkx'


def test_default_does_not_call_engine(grid, monkeypatch):
    import genesis.states as states
    import genesis.metrics as metrics
    import genesis.best_points as points
    import genesis.mclp as mclp
    import fire_units.mclp as fire_mclp

    def forbidden():
        pytest.fail('движок вызван без явного включения')

    for module in (states, metrics, points, mclp, fire_mclp):
        monkeypatch.setattr(module, 'get_engine', forbidden)
    state, metric = FirstArrivalUnitState(), ArrivalTime()
    times, _ = state(env=grid, points=[0, 63])
    expected = metric(times)
    assert NodesMetric(state, metric)(env=grid, nodes=[0, 63]) == expected
    assert NodeMetric(state, metric)(env=grid, node=0) == metric(state(env=grid, points=[0])[0])
    selector = RandomNodesSelector()
    assert BestNodesGA(state, metric, selector)._fit_function(grid, [0, 63]) == expected
    assert BestNodesSA(state, metric, selector)._calculate_energy(grid, [0, 63]) == expected
    assert BestNodesGAKopt(state, metric, None, selector)._fit_function(grid, [0, 63]) == expected
    assert get_atm(grid, data=pd.DataFrame({'node': [0, 63]}), print_calc_states=False).shape == (2, 64)
    # Векторизация метрики тоже не включается молча.
    with monkeypatch.context() as patch:
        patch.setattr(pd.Series, 'to_numpy', forbidden)
        assert CoverIndex(2)(pd.Series([1.0, 2.0, 3.0])) == pytest.approx(200 / 3)
    gwo = BestNodeGWO(state, metric)
    assert gwo._find_closest_node_to_three_weighted(grid, [0, 27, 63]) in grid
    assert gwo._shortest_path_within_distance(grid, 0, 63, 4)[0] == 0
    assert 0 in gwo._search(grid, 0, 1)


@pytest.mark.parametrize('backend', ['networkx', 'scipy'])
def test_service_zone_copy_only_in_legacy(grid, backend):
    if backend == 'scipy':
        require_scipy()
    frozen = []

    def point(env, start_point, **kwargs):
        frozen.append(nx.is_frozen(env))
        return start_point, 0

    dynamic = {0: 'A', 63: 'B'}
    algorithm = BestNodesKoptG(FirstArrivalUnitState(), ArrivalTime(), point, iterations=1)
    with use_backend(backend):
        algorithm(env=grid, dynamic_nodes=dynamic)
    assert frozen == [backend == 'scipy'] * 2


def test_fast_state_and_atm_are_actually_used(grid, monkeypatch):
    require_scipy()
    engine = backends.get_engine()
    calls = []
    for name in ('first_arrival', 'arrival_distances'):
        original = getattr(engine, name)

        def spy(*args, _name=name, _original=original, **kwargs):
            calls.append(_name)
            return _original(*args, **kwargs)

        monkeypatch.setattr(engine, name, spy)
    with use_backend('scipy'):
        FirstArrivalUnitState()(env=grid, points=[0])
        get_atm(grid, data=pd.DataFrame({'node': [0]}), print_calc_states=False)
    assert calls == ['first_arrival', 'arrival_distances']
    assert get_backend() == 'networkx'


def test_custom_metric_subclass_is_not_bypassed(grid):
    require_scipy()

    class CustomArrival(ArrivalTime):
        def __call__(self, state, **kwargs):
            return 12345.0

    with use_backend('scipy'):
        assert NodesMetric(FirstArrivalUnitState(), CustomArrival())(env=grid, nodes=[0]) == 12345.0


def test_gwo_callable_weight_uses_networkx(grid, monkeypatch):
    require_scipy()
    import genesis.best_points as points

    def forbidden():
        pytest.fail('callable-вес передан в движок')

    weight = lambda u, v, edges: min(d['travel_time'] for d in edges.values())
    gwo = BestNodeGWO(FirstArrivalUnitState(), ArrivalTime())
    expected = gwo._find_closest_node_to_three_weighted(grid, [0, 27, 63], weight=weight)
    with use_backend('scipy'):
        monkeypatch.setattr(points, 'get_engine', forbidden)
        assert gwo._find_closest_node_to_three_weighted(grid, [0, 27, 63], weight=weight) == expected


def test_speed_change_clears_cache_after_leaving_fast_context():
    require_scipy()
    from graphs.speeds import kmh_to_mm, set_graph_travel_times
    graph = nx.MultiDiGraph()
    graph.add_edge(0, 1, highway='residential', length=1000.0)
    set_graph_travel_times(graph, [30] * 5, kmh_to_mm)
    with use_backend('scipy'):
        engine = backends.get_engine()
        old = engine.graph_index(graph)
    set_graph_travel_times(graph, [60] * 5, kmh_to_mm)
    with use_backend('scipy'):
        new = engine.graph_index(graph)
        assert new is not old
        assert new.adjacency[0, 1] == pytest.approx(old.adjacency[0, 1] / 2)


def test_without_scipy_in_fresh_process():
    # Блокируем весь scipy до импорта Genesis и его зависимостей.
    # Нельзя ограничиться удалением из sys.modules уже загруженного движка.
    script = textwrap.dedent('''
        import importlib.abc
        import sys
        class NoScipy(importlib.abc.MetaPathFinder):
            def find_spec(self, fullname, path=None, target=None):
                if fullname == 'scipy' or fullname.startswith('scipy.'):
                    raise ModuleNotFoundError('scipy unavailable for test', name=fullname)
        sys.meta_path.insert(0, NoScipy())
        import genesis.states, genesis.mclp, genesis.lscp, genesis.best_points, genesis.metrics
        import fire_units.mclp, fire_units.metrics, graphs.speeds
        import networkx as nx
        import pandas as pd
        from genesis.backends import get_backend, use_backend
        from genesis.states import FirstArrivalUnitState, get_atm
        from genesis.metrics import CoverIndex
        from graphs.speeds import set_graph_travel_times, kmh_to_mm
        assert get_backend() == 'networkx'
        G = nx.MultiDiGraph()
        G.add_edge(0, 1, travel_time=2.0, highway='residential', length=1000.0)
        times, _ = FirstArrivalUnitState(delay=0)(env=G, points=[0])
        assert times.to_dict() == {0: 0.0, 1: 2.0}
        assert CoverIndex(2)(times) == 100
        m = get_atm(G, data=pd.DataFrame({'node': [1]}), delay=0, print_calc_states=False)
        assert m.loc[0, 0] == 2.0
        set_graph_travel_times(G, [30] * 5, kmh_to_mm)
        assert 'genesis.engine' not in sys.modules
        assert 'scipy' not in sys.modules
        try:
            with use_backend('scipy'):
                raise AssertionError('entered missing backend')
        except ModuleNotFoundError as exc:
            assert 'genesis-spatial-opt[fast]' in str(exc)
        else:
            raise AssertionError('missing dependency not reported')
        assert get_backend() == 'networkx'
        assert 'genesis.engine' not in sys.modules
        assert FirstArrivalUnitState(delay=0)(env=G, points=[0])[0][1] == 2.0
        print('no-scipy: OK')
    ''')
    env = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1]))
    result = subprocess.run([sys.executable, '-c', script], env=env, text=True,
                            capture_output=True, timeout=60)
    assert result.returncode == 0, result.stdout + result.stderr
    assert 'no-scipy: OK' in result.stdout
