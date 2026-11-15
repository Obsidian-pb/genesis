'''
Общие настройки тестов
'''

import random

import numpy as np
import pytest


@pytest.fixture(autouse=True)
def fixed_seed():
    '''
    Фиксирует генераторы случайных чисел перед каждым тестом:
    результаты стохастических алгоритмов воспроизводимы и не зависят от порядка тестов
    '''
    random.seed(0)
    np.random.seed(0)


@pytest.fixture(scope='session')
def grid():
    '''
    Сетка 8x8 узлов, ребро 1000 м, 30 км/ч - 2 минуты на ребро.
    Оптимум по среднему и максимальному времени прибытия - центральные узлы 27, 28, 35, 36
    '''
    from graphs.algorithms import generate_grid_graph
    return generate_grid_graph(8, 8, step=1000, speed=30, add_geometry=False)


@pytest.fixture(scope='session')
def grid_buildings(grid):
    '''
    Синтетические здания на сетке: на узлах, кратных 3, - по два здания.
    `pop` - вес здания (номер узла + 1), `demand` - спрос
    '''
    import pandas as pd
    rows = []
    for node in grid.nodes():
        for _ in range(2 if node % 3 == 0 else 1):
            rows.append({'node': node, 'pop': node + 1, 'demand': 1.0})
    return pd.DataFrame(rows)
