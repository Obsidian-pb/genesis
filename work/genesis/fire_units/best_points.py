'''
Дополнительные функции расчета лучшего узла,
учитывающие специфику пожарных подразделений
'''


import networkx as nx
import pandas as pd
import numpy as np


from ..genesis.best_points import BestNodeHillClimbing, BestNodesHalfDiameter
from ..genesis.core import MetricBase, StateBase
from ..genesis.metrics import ArrivalTime
from ..genesis.states import FirstArrivalUnitState


class BestNodeHillClimbing_maxMean_Metric(BestNodeHillClimbing):
    def __init__(self, 
                 state_function: StateBase,
                 metric_function: MetricBase = None,
                 appr_val: float = 0.95,
                 all_neighbors: bool = True,
                 **kwargs) -> None:
        super().__init__(state_function, metric_function, appr_val, all_neighbors, **kwargs)

    def __call__(self, env: nx.MultiDiGraph,
                 area: pd.Series = None,
                 start_node: int = None,
                 debug_route: bool = False,
                 node_calc_end_function: callable = None,
                 **kwargs):

        bnch_max = BestNodeHillClimbing(state_function=self.state_function,
                                        metric_function=ArrivalTime(np.max), appr_val=self.appr_val, all_nodes=self.all_neighbors)
        bnch_mean = BestNodeHillClimbing(state_function=self.state_function,
                                         metric_function=ArrivalTime(), appr_val=self.appr_val, all_nodes=self.all_neighbors)
        bnch_meetric = BestNodeHillClimbing(state_function=self.state_function,
                                         metric_function=self.metric_function, appr_val=self.appr_val, all_nodes=self.all_neighbors)

        best_node, best_metric =     bnch_max(env=env, area=area, start_node=start_node)
        best_node, best_metric =    bnch_mean(env=env, area=area, start_node=best_node)
        best_node, best_metric = bnch_meetric(env=env, area=area, start_node=best_node)

        # выполняем функцию завершения расчета для узла
        if node_calc_end_function:
            node_calc_end_function()

        return best_node, best_metric
    

class BestNodeHillClimbingHD(BestNodeHillClimbing):
    '''
    Расчет лучшего узла с использованием алгоритма
    Hill Climbing и предварительным определением центра диаметра графа.

    
    '''
    def __init__(self,
                 state_function: StateBase,
                 metric_function: MetricBase = None,
                 appr_val: float = 0.95,
                 all_neighbors: bool = True,
                 **kwargs) -> None:
        super().__init__(state_function, metric_function, appr_val, all_neighbors, **kwargs)

    def __call__(self, env: nx.MultiDiGraph,
                 area: pd.Series = None,
                 start_node: int = None,
                 debug_route: bool = False,
                 node_calc_end_function: callable = None,
                 **kwargs):

        bnhd = BestNodesHalfDiameter()
        bnhc = BestNodeHillClimbing(state_function=self.state_function,
                                         metric_function=self.metric_function,
                                         appr_val=self.appr_val,
                                         all_nodes=self.all_neighbors)

        start_node = bnhd(env=env, area=area)
        best_node, best_metric = bnhc(env=env, area=area, start_node=start_node)

        # выполняем функцию завершения расчета для узла
        if node_calc_end_function:
            node_calc_end_function()

        return best_node, best_metric