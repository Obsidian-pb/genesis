'''
Алгоритмы работы с графами

'''

from collections import defaultdict

import numpy as np
import math

import osmnx as ox
from osmnx import utils
import networkx as nx
import geopandas as gpd
from shapely.ops import unary_union, transform
from shapely.geometry import MultiLineString

from scipy.spatial import cKDTree


def fix_highway_list(edge):
    '''
    Функция исправления типа улицы, для случая, когда тип указан как список
    '''
    if isinstance(edge, list):
        return edge[0]
    return edge


def floor_coords(geoms):
    """Округляет координаты геометрии до целых чисел в меньшую сторону"""
    def floor_coord(x, y):
        #return (math.floor(x), math.floor(y))
        return (round(x, -1), round(y, -1))
    
    return transform(floor_coord, geoms)
    # for geom in geoms:
    #     for coord in geom.coords:
    #         for i in range(len(coord)):
    #             coord[i] = math.floor(coord[i])
    #             return geom




def graph_rise_from_gpkg(roads: gpd.GeoDataFrame,
                         oneway_field_name: str = 'oneway',
                         # lanes_field_name: str = 'lanes',  # Сейча не реализовано
                         reversed_field_name: str = 'reversed',
                         ):
    '''
    Алгоритм собирает граф дорожной сети на основе геометрии входного векторного GeoDataFrame

    Аргументы
    ---------
    `roads`: gpd.GeoDataFrame
        Датафрейм дорог
    `oneway_field_name`: str
        Поле в котором хранятся сведения о односторонности дороги
    `reversed_field_name`: str
        Поле в котором хранятся сведения о направлении движения

    Возвращает
    ----------
    `nx.MultiDiGraph`
        Граф улично-дорожной сети
    ``
    '''
    import warnings

    # Проверка наличия колонок
    #missing_cols = [col for col in [oneway_field_name, reversed_field_name] if col not in roads.columns]
    #if missing_cols:
    #    raise ValueError(f"В GeoDataFrame отсутствуют необходимые колонки: {missing_cols}")

    # Запомним исходную СК
    crs = roads.crs
    
    # Спроектируем DataFrame в местную метрическую систему координат
    try:
        roads_p = ox.projection.project_gdf(roads)
    except Exception:
        roads_p = roads

    # Округляем координаты геометрии до целых чисел
    roads_p['geometry'] = roads_p['geometry'].apply(floor_coords)

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

        # Обработка MultiLineString
        # Это нужно проверить
        if isinstance(geometry, MultiLineString):
            lines = geometry.geoms
        else:
            lines = [geometry]

        road_data = road  #[columns_list]
        road_data = {k: v[0] if isinstance(v, list) else v for k, v in road_data.items()}

        # Перебираем все линии в геометрии (может быть несколько для MultiLineString)
        for line in lines:
            coords = list(line.coords)

            # Добавляем узлы в граф
            for coord in coords:
                # # Используем KD-дерево для быстрого поиска близких точек
                # tree = cKDTree(list(nodes_dict.keys()))
                # # Находим все пары близких точек
                # nearest = tree.query_ball_point([coord], 1)

                # if nearest:
                if coord not in nodes_dict:
                    nodes_dict[coord] = node_id
                    node_id += 1
                G.add_node(nodes_dict[coord], x=coord[0], y=coord[1])

            # Добавляем ребра в граф
            for coord1, coord2 in zip(coords[:-1], coords[1:]):
                length = ox.distance.euclidean(y1=coord1[1], x1=coord1[0],
                                              y2=coord2[1], x2=coord2[0])

                # Универсальная обработка oneway
                oneway = road_data.get(oneway_field_name, False)
                # Проверка на NaN
                if isinstance(oneway, float) and np.isnan(oneway):
                    oneway = False
                elif isinstance(oneway, str):
                    oneway = oneway.lower() in ['yes', 'true', '1']
                elif isinstance(oneway, (int, float)):
                    oneway = bool(oneway)
                road_data[oneway_field_name] = oneway

                # Универсальная обработка reversed
                reversed_val = road_data.get(reversed_field_name, False)
                if isinstance(reversed_val, float) and np.isnan(reversed_val):
                    reversed_val = False
                elif isinstance(reversed_val, str):
                    reversed_val = reversed_val.lower() in ['yes', 'true', '1']
                elif isinstance(reversed_val, (int, float)):
                    reversed_val = bool(reversed_val)
                road_data[reversed_field_name] = reversed_val

                if not oneway:
                    # Двусторонняя дорога — ребра в обе стороны
                    key = existed_edges_dict.get((nodes_dict[coord2], nodes_dict[coord1]), 0)
                    G.add_edge(nodes_dict[coord2], nodes_dict[coord1], key,
                               **road_data, length=length)
                    existed_edges_dict[(nodes_dict[coord2], nodes_dict[coord1])] = key + 1

                    key = existed_edges_dict.get((nodes_dict[coord1], nodes_dict[coord2]), 0)
                    G.add_edge(nodes_dict[coord1], nodes_dict[coord2], key,
                               **road_data, length=length)
                    existed_edges_dict[(nodes_dict[coord1], nodes_dict[coord2])] = key + 1
                else:
                    # Односторонняя дорога
                    if reversed_val:
                        # Движение в обратном направлении
                        key = existed_edges_dict.get((nodes_dict[coord2], nodes_dict[coord1]), 0)
                        G.add_edge(nodes_dict[coord2], nodes_dict[coord1], key,
                                   **road_data, length=length)
                        existed_edges_dict[(nodes_dict[coord2], nodes_dict[coord1])] = key + 1
                    else:
                        # Движение в прямом направлении
                        key = existed_edges_dict.get((nodes_dict[coord1], nodes_dict[coord2]), 0)
                        G.add_edge(nodes_dict[coord1], nodes_dict[coord2], key,
                                   **road_data, length=length)
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