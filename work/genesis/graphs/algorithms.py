'''
Алгоритмы работы с графами

'''

import osmnx as ox
from osmnx import utils
import networkx as nx
import geopandas as gpd



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
        roads_p = ox.project_gdf(roads)
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
                if road['reversed']:
                    # Получаем ключ ребра
                    key = existed_edges_dict.get((nodes_dict[coord2], nodes_dict[coord1]), 0)
                    # Добавляем ребро
                    G.add_edge(nodes_dict[coord2], nodes_dict[coord1], key,
                               **road_data,
                               length=length)
                    # Указываем количество имеющихся ребер
                    existed_edges_dict[(nodes_dict[coord2], nodes_dict[coord1])] = key + 1
                else:
                    # Получаем ключ ребра
                    key = existed_edges_dict.get((nodes_dict[coord1], nodes_dict[coord2]), 0)
                    # Добавляем ребро
                    G.add_edge(nodes_dict[coord1], nodes_dict[coord2], key,
                               **road_data,
                               length=length)
                    # Указываем количество имеющихся ребер
                    existed_edges_dict[(nodes_dict[coord1], nodes_dict[coord2])] = key + 1
    
    # перепроецируем граф к исходной системе координат
    G = ox.project_graph(G, to_crs=crs)

    return G
