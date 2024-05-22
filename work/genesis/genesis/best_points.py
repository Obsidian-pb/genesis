'''
Алгоритмы решения задачи MCLP (Maximum Covering Location Problem).

Поиск оптимальных узлов графа с точки зрения максимизации покрытия.
'''

import numpy as np
from genesis.core import BestPoints, MetricBase, StateBase
# from genesis.metrics import arrival_time, nodes_metric
# from genesis.states import voronoi_forest
# from genesis.swiss_knife import MSF




class BestNodesFull(BestPoints):
    '''
        Поиск лучших узлов графа полным перебором. 
        Могут быть возвращены только узлы из которых можно попасть в большую часть других узлов графа.
        Если таковых узлов нет, возвращается ошибка некорректности графа. 
        (граф должен быть проверен на корректность прежде чем будет передан функции)
        
        Узлы для которых метрика не может быть вычислена (например слабо связанные 
        с основным графом) не учитываются. 

        ## Важно
        Следует помнить, что некорректные узлы в случае их учета посредством снижения appr_val могут 
        давать искаженное представление о метриках графа. При этом в реальности граф дорожной сети 
        как правило изобилует слабосвязанными узлами, поэтому учет только узлов обеспечивающих 100%
        достижимость всего графа может приводить к принципиальной невозможности расчета.
    '''
    def __init__(self,
                 state_function: StateBase,
                 metric_function: MetricBase,
                 appr_val = 0.95,
                 **kwargs) -> None:
        '''
        `state_function` : StateBase
            Функция расчета состояния среды
        `metric_function` : MetricBase
            Функция оценки. Если не указана, используется оценка по минимальному расстоянию.
        `appr_val`: = 0.95
            Доля узлов графа, покрытие которой считается приемлемой для принятия расчетной метрики. 
            Если при расчете метрик, из стартового узла (узлов) достижимо меньшее количество узлов,
            то такой узел не рассматривается.
        '''
        self.appr_val = appr_val
        super().__init__(state_function, metric_function, **kwargs)

    def __call__(self, env, area=None, nodes_list=None, node_calc_end_function=None, **kwargs):
        '''
        ## Параметры
        `env` : MultiDiGraph (G)
            Граф дорожной сети
        `area`: pd.Series = None
            Маска узлов графа. Значениями True отмечены узлы графа - цели расчета леса Вороного.
            Если не указана, расчет производится для всех узлов графа.
        `nodes_list`:list=None
            Если указано, то рассматриваются только переданные узлы.

        ## Возвращает
        tuple: (list(int), float)
            Множество - (идентификатор узла, значение метрики узла)
        '''

        if nodes_list is None:
            nodes_list = env.nodes()

        appr_nodes_count = int(len(nodes_list) * self.appr_val)
        
        best_metric = None
        best_node = None
        for node in nodes_list:

            # расчет среды
            times, _ = self.state_function(env=env, points=[node], area=area, **kwargs)

            # проверка на корректность охвата графа
            if len(times)>=appr_nodes_count:

                # расчет метрики среды для текущего узла `node`
                node_metric = self.metric_function(times, **kwargs)

                # если лучшая метрика еще не указана, присваиваем текущее значение
                if best_metric is None:
                    best_metric = node_metric
                    best_node = node

                # проверяем лучше ли метрика среды для текущего узла, чем лучшая до этого
                # if best_metric > node_metric:
                if self.metric_function.compare(best_metric, node_metric) == node_metric:
                    best_metric = node_metric
                    best_node = node
                
                # выполняем функцию завершения расчета для узла
                if node_calc_end_function:
                    node_calc_end_function()

        return best_node, best_metric







# def best_node_full(G,
#                    path_function=MSF,
#                    metric_function=arrival_time(np.mean),
#                    voronoi_function=voronoi_forest,
#                    nodes_list=None,
#                    node_calc_end_function=None,
#                    reduce=True,
#                    **kwargs):
#    '''
        

#         ## Параметры
#         `G` : MultiDiGraph
#             Граф дорожной сети
#         `path_function` : function
#             Функция расчета пути вида nx.multi_source_dijkstra_path_length 
#             - расчет от множества узлов.
#         `metric_function` : function
#             Функция оценки. Если не указана, используется оценка по минимальному расстоянию.
#         `weight` : str
#             имя поля ребер ГДС содержащего вес пути (в данном случае имеется в виду время следования)
#         `appr_val`: = 0.95
#             Доля узлов графа, покрытие которой считается приемлемой для принятия расчетной метрики. 
#             Если при расчете метрик, из стартового узла (узлов) достижимо меньшее количество узлов,
#             то такой узел не рассматривается.
#         `possible_nodes`:list=None
#             Если указано, то рассматриваются только переданные узлы.
#         `reduce` : bool = True
#             Если True - при сравнении значений метрик выбирается меньшее значение, иначе большее. 
#             При расчете метрик для которых чем меньше значение тем лучше (среднее, максимальное 
#             время и т.д.) необходимо использовать reduce=True, 
#             при расчете метрик для которых чем больше тем лучше (ИП) - True

#         ## Возвращает
#         tuple: (list(int), float)
#             Множество - (идентификатор узла, значение метрики узла)
#         '''
   
#    if nodes_list is None:
#         nodes_list = G.nodes()
   
#    best_metric = None
#    best_node = None
#    for node in nodes_list:
#       node_metric = nodes_metric(G=G,
#             sources=[node],
#             path_function=path_function,
#             metric_function=metric_function,
#             voronoi_function=voronoi_function,
#             **kwargs)
#       # здесь должна быть проверка на корректность охвата графа
#       if best_metric is None:
#          best_metric = node_metric
#          best_node = node
#       if best_metric > node_metric:
#          best_metric = node_metric
#          best_node = node
#       if node_calc_end_function:
#          node_calc_end_function()
      
#    return best_node, best_metric
