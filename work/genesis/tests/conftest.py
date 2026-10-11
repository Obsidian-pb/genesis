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
