'''
Алгоритмы работы с графами

'''

from collections import defaultdict

import osmnx as ox
from osmnx import utils
import networkx as nx
import geopandas as gpd
from shapely.ops import unary_union



def fix_highway_list(edge):
    '''
    Функция исправления типа улицы, для случая, когда тип указан как список
    '''
    if isinstance(edge, list):
        return edge[0]
    return edge


def graph_rise_from_gpkg(roads: gpd.GeoDataFrame,
                         columns_list: list = ['name', 'highway', 'oneway', 'lanes', 'reversed']):
    '''
    Алгоритм собирает граф дорожной сети на основе геометрии входного векторного GeoDataFrame

    # Аргументы
    `roads`: gpd.GeoDataFrame
        Датафрейм дорог
    `columns_list`: list
        Список полей, которые должны сохраниться в итоговом графе
    '''

    # Запомним исходную СК
    crs = roads.crs
    
    # Спроектируем DataFrame в местную метрическую систему координат
    try:
        roads_p = ox.projection.project_gdf(roads)
    except:
        roads_p = roads
        pass

    # Создаем пустой граф
    metadata = {
            "created_date": utils.ts(),
            "created_with": f"OSMnx {ox.__version__}",
            "crs": roads_p.crs
        }
    G = nx.MultiDiGraph(**metadata)

    nodes_dict = {}
    node_id = 0

    # Словарь имеющихся ребер (для учета повторов)
    existed_edges_dict = {}

    # Перебираем все строки с записями фрагментов дорог
    for _, road in roads_p.iterrows():
        geometry = road['geometry']

        Warning('Необходимо добавить проверку наличия соответствующих колонок')
        road_data = road[columns_list]
        road_data = {k:v[0] if isinstance(v, list) else v for k,v in road_data.items()}

        # Координаты всех точек в линии
        coords = list(geometry.coords)

        # Добавляем узлы в граф
        for coord in coords:
            if not coord in nodes_dict:
                nodes_dict[coord] = node_id
                node_id += 1

            G.add_node(nodes_dict[coord], x = coord[0], y = coord[1])

        # Добавляем ребра в граф
        for coord1, coord2 in zip(coords[:-1], coords[1:]):
            # Важно! Здесь сейчас длина просто берется из данных указанных в участке дороги на карте. НО должна вычисляться!
            length = ox.distance.euclidean(y1 = coord1[1], x1 = coord1[0],
                                        y2 = coord2[1], x2 = coord2[0])

            # Добавляем ребра в обе стороны
            if road['oneway'] == False:
                # Получаем ключ ребра
                key = existed_edges_dict.get((nodes_dict[coord2], nodes_dict[coord1]), 0)
                # Добавляем ребро
                G.add_edge(nodes_dict[coord2], nodes_dict[coord1], key,
                           **road_data,
                           length=length)
                # Указываем количество имеющихся ребер
                existed_edges_dict[(nodes_dict[coord2], nodes_dict[coord1])] = key + 1
            else:
                # Добавляем ребро в обратную сторону и в прямую
                # if road['reversed']:
                #     # Получаем ключ ребра
                #     key = existed_edges_dict.get((nodes_dict[coord2], nodes_dict[coord1]), 0)
                #     # Добавляем ребро
                #     G.add_edge(nodes_dict[coord2], nodes_dict[coord1], key,
                #                **road_data,
                #                length=length)
                #     # Указываем количество имеющихся ребер
                #     existed_edges_dict[(nodes_dict[coord2], nodes_dict[coord1])] = key + 1
                # else:
                # Получаем ключ ребра
                key = existed_edges_dict.get((nodes_dict[coord1], nodes_dict[coord2]), 0)
                # Добавляем ребро
                G.add_edge(nodes_dict[coord1], nodes_dict[coord2], key,
                            **road_data,
                            length=length)
                # Указываем количество имеющихся ребер
                existed_edges_dict[(nodes_dict[coord1], nodes_dict[coord2])] = key + 1

    # перепроецируем граф к исходной системе координат
    G = ox.projection.project_graph(G, to_crs=crs)

    return G


def net_overlay(G_master:nx.MultiDiGraph, key_nodes:list, weight='length', cutoff=240):
    '''
    Наложение сети. Экспериментально! Требует проверки и уточнения!

    Выбираются ключевые узлы ГДС между которыми выстраиваются кратчайшие 
    маршруты становящиеся ребрами СГДС-- (Граф Дорожной Сети Субъектового уровня 
    максимальный вариант упрощения). 

    Аргументы
    ---------
    G_master: MultiDiGraph
        СГДС
    key_nodes: list
        список ключевых узлов которые должны стать вершинами нового графа
    weight : str
        Имя поля содержащего сведения о весе ребра (км, или время и что-то иное)

    Возвращает
    ----------
    MultiDiGraph
        Упрощенный граф дорожной сети
    '''

    # 1. Построить зоны достижимости всех подразделений с учетом взаимного влияния
    destination_areas = nx.multi_source_dijkstra_path(G_master, key_nodes, weight=weight)

    # 2. Определить смежность подразделений
    links_from=[]
    links_to=[]
    links_list=[]
    for node in destination_areas.keys():
        if len(G_master[node])>0:
            from_node = destination_areas[node][0]
            for next_node in list(G_master[node]):
                to_node=destination_areas[next_node][0]
                if from_node!=to_node:
                    if not (from_node, to_node) in links_list:
                        links_from.append(from_node)
                        links_to.append(to_node)
                        links_list.append((from_node, to_node))

    # 3. Найти кратчайшие пути между 
    links_paths = ox.shortest_path(G_master, links_from, links_to, weight=weight)

    # 4. Объединить ребра и ключевые точки в СГДС--
    G_new = _paths_to_graph(G_master, links_paths, weight=weight)

    return G_new

def _paths_to_graph(G, paths, weight='length'):
    '''
    Возвращает граф полученный из путей на основе некоторого базового графа.

    Требует доработки

    Аргументы
    ---------
    G : MultiDiGraph
        Граф дорожной сети
    paths : list(list)
        Список списков - список путей, где каждый путь 
        список последовательных узлов
    weight : str
        Имя поля содержащего сведения о весе ребра (км, или вермя и что-то иное)
    
    Возвращает
    ----------
    MultiDiGraph
        Упрощенный граф дорожной сети
    '''
    G_new = ox.graph.nx.MultiDiGraph()
    g_edges = ox.graph_to_gdfs(G, edges=True, nodes=False)
    for path in paths:
        lines=[]
        length=0
        weight_add=0
        pseudo_osmid = 0
        hws = defaultdict(lambda: 0)    # Словарь длины дорог в зависимости от типа
        try:
            for u, v in zip(path[:-1], path[1:]):
                edge_data = g_edges.loc[u,v,0]
                # if 'geometry' in G.edges[u,v,0].keys():
                if 'geometry' in edge_data.keys():                    
                    lines.append(edge_data['geometry'])
                    # print(edge_data['geometry'])
                if 'length' in edge_data.keys():
                    hw_val = edge_data['length']
                    length+=hw_val
                    # Добавляем длину по типу дорог
                    hw = edge_data['highway']
                    if isinstance(hw, list):
                        hw=hw[0]
                    hws[hw]+=hw_val
                if weight!='length':
                    if weight in edge_data.keys():
                        hw_val = edge_data[weight]
                        weight_add+=hw_val
                        # Добавляем длину по типу дорог
                        hw = edge_data['highway']
                        if isinstance(hw, list):
                            hw=hw[0]
                        hws[hw]+=hw_val

            G_new.add_nodes_from([ (path[0], G.nodes(data=True)[path[0]]) ])
            G_new.add_nodes_from([ (path[-1], G.nodes(data=True)[path[-1]]) ])
            data={
                'osmid': pseudo_osmid,
                'lanes': '2',
                'highway': max(hws, key=hws.get),     # 'tertiary' # до 11/01/2024: 
                'oneway': False,
                'length': length,
                'geometry': unary_union(lines)
            }
            # print(unary_union(lines))
            # print(lines)
            if weight!='length':
                data[weight]=weight_add
        
            G_new.add_edges_from([ (path[0],path[-1], data) ])

            pseudo_osmid += 1

        except TypeError:
            print("gds._paths_to_graph: проверить работоспособность путей длиной 0", path)
        
    G_new.graph["crs"]='WGS 84'
    
    return G_new