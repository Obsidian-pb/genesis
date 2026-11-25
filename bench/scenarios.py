'''
Сценарии сравнения ядер genesis.

Сценарии используют только интерфейс исходного проекта, поэтому одинаково запускаются
на исправленной версии, на оригинале автора и (через адаптер) на новом ядре.
Каждый сценарий - функция без аргументов, возвращающая словарь с результатом.
'''

import random

import networkx as nx
import numpy as np
import osmnx as ox
import pandas as pd

from genesis.best_points import (BestNodeBee, BestNodeCircleZoom, BestNodeGWO, BestNodeHillClimbing,
                                 BestNodeHillClimbing_maxMean, BestNodeMonkey, BestNodesFull,
                                 BestNodeSquareZoom)
from genesis.lscp import LSCP_ADD, LSCPCommon, drop_trash_points
from genesis.mclp import BestNodesGA, BestNodesKoptG, BestNodesSA, NodesMetric
from genesis.metrics import ArrivalTime, CoverIndex
from genesis.point_selectors import FarNodeSelector, GenesisNodeSelector, RandomNodesSelector
from genesis.states import FirstArrivalUnitState, get_atm
from genesis.stop_cases import ItersStopCase
from fire_units.best_points import BestNodeHillClimbing_maxMean_Metric, BestNodeHillClimbingHD
from fire_units.settings import DEFAULT_SPEEDS
from graphs.algorithms import generate_grid_graph
from graphs.speeds import kmh_to_mm, set_graph_travel_times

try:
    from genesis.hybridisation import Hybridization
except ImportError:  # pragma: no cover
    Hybridization = None
try:
    from fire_units.mclp import BestNodesGAKopt
except ImportError:  # pragma: no cover
    BestNodesGAKopt = None

SEEDS = range(5)
DATA = 'work/genesis/tests/data/test_rng.ml'


def load_graphs():
    '''
    Сетка 8x8 и граф Сосновоборска (упрощенный, наибольший сильносвязный компонент, 1935 узлов)
    '''
    grid = generate_grid_graph(8, 8, step=1000, speed=30, add_geometry=False)
    G = ox.load_graphml(DATA)
    set_graph_travel_times(G, DEFAULT_SPEEDS, kmh_to_mm)
    G = ox.simplify_graph(G)
    G = G.subgraph(max(nx.strongly_connected_components(G), key=len)).copy()
    return {'grid': grid, 'sosnovoborsk': G}


def _units(G, count, seed):
    nodes = sorted(G.nodes())
    return {n: f'U{i}' for i, n in enumerate(random.Random(seed).sample(nodes, count))}


def _plain(node):
    '''
    Номер узла numpy -> int для JSON
    '''
    return node.item() if isinstance(node, np.generic) else node


def _nodes(result):
    nodes = result[0]
    if isinstance(nodes, dict):
        return sorted(_plain(n) for n in nodes.keys())
    if isinstance(nodes, (list, set, tuple)):
        return sorted(_plain(n) for n in nodes)
    return _plain(nodes)


def _value(result):
    return None if result[1] is None else float(result[1])


def build(graphs):
    '''
    Список сценариев: (id, вид, функция). Вид: state, metric, deterministic, stochastic
    '''
    st = FirstArrivalUnitState()
    out = []

    for gname, G in graphs.items():
        thr = 6 if gname == 'grid' else 5
        metrics = {'mean': ArrivalTime(), 'max': ArrivalTime(np.max), f'cover{thr}': CoverIndex(thr)}
        for count in (1, 3, 5):
            units = _units(G, count, seed=count)

            def state_case(G=G, units=units):
                times, nearest = st(env=G, points=units)
                return {'times': {str(k): float(v) for k, v in times.sort_index().items()},
                        'nearest': {str(k): v for k, v in nearest.sort_index().items()}}
            out.append((f'{gname}/state/{count}', 'state', state_case))

            for mname, m in metrics.items():
                def metric_case(G=G, units=units, m=m):
                    return {'value': float(NodesMetric(st, m)(G, list(units)))}
                out.append((f'{gname}/metric/{mname}/{count}', 'metric', metric_case))

        # Одна точка, детерминированные
        single = {
            'Full': lambda m: BestNodesFull(st, m),
            'HillClimbing': lambda m: BestNodeHillClimbing(st, m),
            'HillClimbing_maxMean': lambda m: BestNodeHillClimbing_maxMean(st, m),
            'fu.maxMean_Metric': lambda m: BestNodeHillClimbing_maxMean_Metric(st, m),
            'fu.HillClimbingHD': lambda m: BestNodeHillClimbingHD(st, m),
        }
        for aname, make in single.items():
            for mname, m in metrics.items():
                def single_case(G=G, make=make, m=m):
                    r = make(m)(env=G, start_point=sorted(G.nodes())[0])
                    return {'nodes': _nodes(r), 'value': _value(r)}
                out.append((f'{gname}/single/{aname}/{mname}', 'deterministic', single_case))

        # Одна точка, стохастические
        stoch_single = {
            'Bee': lambda m: BestNodeBee(st, m, scouts_count=20, best_scouts_count=3),
            'Monkey': lambda m: BestNodeMonkey(st, m),
            'SquareZoom': lambda m: BestNodeSquareZoom(st, m),
            'CircleZoom': lambda m: BestNodeCircleZoom(st, m),
            'GWO': lambda m: BestNodeGWO(st, m, max_iter=10, pack_size=8),
        }
        for aname, make in stoch_single.items():
            for mname, m in metrics.items():
                def stoch_single_case(G=G, make=make, m=m):
                    runs = []
                    for seed in SEEDS:
                        random.seed(seed)
                        np.random.seed(seed)
                        r = make(m)(env=G)
                        runs.append({'nodes': _nodes(r), 'value': _value(r)})
                    return {'runs': runs}
                out.append((f'{gname}/single/{aname}/{mname}', 'stochastic', stoch_single_case))

        # Несколько подразделений
        start = _units(G, 3, seed=7)
        multi_det = {
            'KoptG': lambda m: BestNodesKoptG(st, m, BestNodeHillClimbing(st, m), iterations=5),
            'LSCPCommon_Far': lambda m: LSCPCommon(BestNodesKoptG(st, m, BestNodeHillClimbing(st, m), iterations=2),
                                                   FarNodeSelector(st), ItersStopCase(2), m),
            'LSCPCommon_Genesis': lambda m: LSCPCommon(BestNodesKoptG(st, m, BestNodeHillClimbing(st, m), iterations=2),
                                                       GenesisNodeSelector(state_function=st, metric_function=m),
                                                       ItersStopCase(2), m),
        }
        for aname, make in multi_det.items():
            for mname, m in metrics.items():
                def multi_det_case(G=G, make=make, m=m, start=start):
                    r = make(m)(env=G, dynamic_nodes=dict(start))
                    return {'nodes': _nodes(r), 'value': _value(r)}
                out.append((f'{gname}/multi/{aname}/{mname}', 'deterministic', multi_det_case))

        multi_stoch = {
            'GA': lambda m: BestNodesGA(st, m, RandomNodesSelector(), population_size=20, epochs=15),
            'SA': lambda m: BestNodesSA(st, m, RandomNodesSelector(), turns=300),
        }
        if BestNodesGAKopt is not None:
            multi_stoch['GAKopt'] = lambda m: BestNodesGAKopt(
                st, m, BestNodesKoptG(st, m, BestNodeHillClimbing(st, m), iterations=1),
                RandomNodesSelector(), population_size=6, epochs=3)
        if Hybridization is not None:
            multi_stoch['Hybridization'] = lambda m: Hybridization(
                st, m, [BestNodesKoptG(st, m, BestNodeHillClimbing(st, m), iterations=2),
                        BestNodesSA(st, m, RandomNodesSelector(), turns=100)])
        for aname, make in multi_stoch.items():
            for mname, m in metrics.items():
                def multi_stoch_case(G=G, make=make, m=m, start=start):
                    runs = []
                    for seed in SEEDS:
                        random.seed(seed)
                        np.random.seed(seed)
                        r = make(m)(env=G, dynamic_nodes=dict(start))
                        runs.append({'nodes': _nodes(r), 'value': _value(r)})
                    return {'runs': runs}
                out.append((f'{gname}/multi/{aname}/{mname}', 'stochastic', multi_stoch_case))

        # LSCP
        def lscp_add_case(G=G, thr=thr):
            nodes_df = ox.graph_to_gdfs(G, edges=False)
            nodes_df['node'] = nodes_df.index
            matrix = get_atm(G, nodes_df, print_calc_states=False)
            r = LSCP_ADD(state_function=st, matrix=matrix, metric_function=CoverIndex(thr), ip_val=thr,
                         stop_case_function=lambda value, **kw: value >= 90)(env=G)
            return {'nodes': _nodes(r), 'value': _value(r)}
        out.append((f'{gname}/lscp/LSCP_ADD/cover{thr}', 'deterministic', lscp_add_case))

        def drop_case(G=G, thr=thr):
            nodes = sorted(G.nodes())
            dyn = {n: f'U{i}' for i, n in enumerate(nodes[::max(1, len(nodes) // 10)])}
            r = drop_trash_points(env=G, state_function=st, metric_function=CoverIndex(thr),
                                  stop_case_function=lambda value, **kw: value >= 40, dynamic_nodes=dyn)
            return {'nodes': _nodes(r), 'value': _value(r)}
        out.append((f'{gname}/lscp/drop_trash_points/cover{thr}', 'deterministic', drop_case))

    return out
