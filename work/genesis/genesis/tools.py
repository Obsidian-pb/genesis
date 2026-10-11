'''
Инструменты обработки используемые в расетах.
'''

from typing import Any

import time
import numpy as np
import pandas as pd
import geopandas as gpd
import logging as lg
import networkx as nx




def get_all_neighbor_nodes(G: nx.Graph, node: int) -> list:
    '''
    Возвращает полный список всех соседних узлов.
    '''
    nnodes = []
    for edge in G.out_edges(node):
        nnodes.append(edge[1])
    for edge in G.in_edges(node):
        nnodes.append(edge[0])
    return nnodes


def multi_source_dijkstra_reversed(G, sources, **kwargs) -> Any:
    '''
    Алгоритм расчета кратчайших маршрутов в точки `source`
    с использованием алгоритма Дейкстры
    в реализации `nx.multi_source_dijkstra`.
    '''
    G = nx.reverse(G.copy())
    return nx.multi_source_dijkstra(G=G, sources=sources, **kwargs)


def list_dict_concat(a:list|dict,b:list|dict) -> list|dict:
    '''
    Корректно склеивает между собой списки и словари.
    При условии, что аргумент `a` и аргумент `b` одного типа.

    #Аргументы
    `a`, `b`: list|dict
        Аргументы которые следует склеить между собой
    '''
    if isinstance(a,list) and isinstance(b,list):
        return a+b
    elif isinstance(a,dict) and isinstance(b,dict):
        return {**a, **b}
    else:
        raise TypeError(f'Аргументы имеют различный тип данных: {a:type(a)}, {b:type(b)}')

def k_v_dict(d, f=min):
    '''
    Получаем номер ключа в словаре которому соответствует значение с
    минимальным/максимальным/средним и т.д. значением, в зависимости
    от функции f.

    Самый быстрый способ.
    '''
    v=list(d.values())
    k=list(d.keys())
    return k[v.index(f(v))]

def get_dict_key(dictionary: dict, value: Any):
    '''
    Получение ключа в словаре по значению

    Аргументы
    ---------
    `dictionary`: dict
        Словарь в котором ищем значение
    `value`: Any
    '''
    for key, value_in_dict in dictionary.items():
        if value_in_dict == value:
            return key
    return None

def get_duplicates_list(seq: list):
    '''
    Получение списка дублирующихся во входящем списке значений

    Аргументы
    ---------
    `seq` (list)  
        Список значений
    '''
    duplicates = []
    unique = []
    for s in seq:
        if s not in unique:
            unique.append(s)
        else:
            duplicates.append(s)
    return duplicates


def normalize_weights(weights) -> np.ndarray:
    '''
    Приводит веса отбора к диапазону [0, 1].
    Если все веса равны, всем особям даются равные веса 1.

    Аргументы
    ---------
    `weights` (list)  
        Веса особей
    '''
    weights = np.asarray(weights, dtype=float)
    w_min, w_max = np.min(weights), np.max(weights)
    if w_max == w_min:
        return np.ones_like(weights)
    return (weights - w_min) / (w_max - w_min)


def ga_crossover(parent_1: dict, parent_2: dict) -> dict:
    '''
    Одноточечное скрещивание особей вида {узел: подразделение}.
    Первая половина подразделений (в порядке `parent_1`) остается в узлах `parent_1`,
    вторая переходит в узлы `parent_2`. Если узел из `parent_2` уже занят,
    подразделение остается в своем узле из `parent_1`.
    Потомок содержит все подразделения родителей, каждое в отдельном узле.

    Аргументы
    ---------
    `parent_1`, `parent_2` (dict)  
        Родительские особи с одинаковым набором подразделений
    '''
    split_point = int(len(parent_1)/2)
    unit_nodes = {unit: node for node, unit in parent_1.items()}
    parent_2_nodes = {unit: node for node, unit in parent_2.items()}
    for unit in list(unit_nodes)[split_point:]:
        node = parent_2_nodes.get(unit)
        if node is not None and node not in unit_nodes.values():
            unit_nodes[unit] = node
    return {node: unit for unit, node in unit_nodes.items()}
