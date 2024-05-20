'''
Алгоритмы решения задачи MCLP (Maximum Covering Location Problem).

Поиск оптимальных узлов графа с точки зрения максимизации покрытия.
'''

import numpy as np
from genesis.estimated_arrival_parameters import arrival_time, nodes_metric
from genesis.optimal_service_areas import voronoi_forest
from genesis.swiss_knife import MSF


def best_node_full(G,
                   path_function=MSF,
                   metric_function=arrival_time(np.mean),
                   voronoi_function=voronoi_forest,
                   nodes_list=None,
                   node_calc_end_function=None,
                   reduce=True,
                   **kwargs):
   '''
        Поиск лучших узлов полным перебором. 
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

        ## Параметры
        `G` : MultiDiGraph
            Граф дорожной сети
        `path_function` : function
            Функция расчета пути вида nx.multi_source_dijkstra_path_length 
            - расчет от множества узлов.
        `metric_function` : function
            Функция оценки. Если не указана, используется оценка по минимальному расстоянию.
        `weight` : str
            имя поля ребер ГДС содержащего вес пути (в данном случае имеется в виду время следования)
        `appr_val`: = 0.95
            Доля узлов графа, покрытие которой считается приемлемой для принятия расчетной метрики. 
            Если при расчете метрик, из стартового узла (узлов) достижимо меньшее количество узлов,
            то такой узел не рассматривается.
        `possible_nodes`:list=None
            Если указано, то рассматриваются только переданные узлы.
        `reduce` : bool = True
            Если True - при сравнении значений метрик выбирается меньшее значение, иначе большее. 
            При расчете метрик для которых чем меньше значение тем лучше (среднее, максимальное 
            время и т.д.) необходимо использовать reduce=True, 
            при расчете метрик для которых чем больше тем лучше (ИП) - True

        ## Возвращает
        tuple: (list(int), float)
            Множество - (идентификатор узла, значение метрики узла)
        '''
   
   if nodes_list is None:
        nodes_list = G.nodes()
   
   best_metric = None
   best_node = None
   for node in nodes_list:
      node_metric = nodes_metric(G=G,
            sources=[node],
            path_function=path_function,
            metric_function=metric_function,
            voronoi_function=voronoi_function,
            **kwargs)
      # здесь должна быть проверка на корректность охвата графа
      if best_metric is None:
         best_metric = node_metric
         best_node = node
      if best_metric > node_metric:
         best_metric = node_metric
         best_node = node
      if node_calc_end_function:
         node_calc_end_function()
      
   return best_node, best_metric
