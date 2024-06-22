'''
Реализация алгоритмов поиска оптимального размещения нескольких наилучшим образом расположенных узлов (MCLP)
'''

import networkx as nx
import pandas as pd
from genesis.core import BestPointsBase, MetricBase, StateBase
from genesis.best_points import NodeMetric


class BestNodesGenesis(BestPointsBase):
    '''
    Поиск лучших узлов для размещения n объектов.
    '''

    def __init__(self,
                 state_function: StateBase,
                 metric_function: MetricBase,
                 best_point_function: BestPointsBase,
                 iterations=5,
                 **kwargs) -> None:
        self.best_point_function = best_point_function
        super().__init__(state_function, metric_function, **kwargs)


    def __call__(self,
                 env:nx.MultiDiGraph,
                 dinamic_nodes: list,
                 static_nodes: list = None,
                 area = None,
                 **kwargs):
        
        if not isinstance(env, nx.MultiDiGraph):
            raise TypeError("Тип переменной `env` должен быть MultiDiGraph!")

        # node_metric_func = NodeMetric(self.state_function, self.metric_function, self.appr_val, err_val=None)

        if static_nodes is None:
            static_nodes = []

        # 1. Расчет состояния 
        times, nearest = self.state_function()(env=env, points=dinamic_nodes+static_nodes)



# ArrivalTime()(times), CoverIndex()(times), CoverIndex(20)(times)

        
