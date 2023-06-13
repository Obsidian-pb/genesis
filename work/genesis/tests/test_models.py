'''

pytest tests/test_models.py  
'''

import pytest

import osmnx as ox
# import networkx as nx
# import numpy as np

from genesis.models import Environment, RoadNetworkGraph
# from genesis.models import SpeedProfile

@pytest.fixture()
def load_G():
    return ox.load_graphml("tests/data/test_rng.ml")

def test_environment_creation():
    E = Environment()
    assert isinstance(E, Environment)



@pytest.mark.xfail()
def test_environment_G_addition_wrong(load_G):
    E = Environment()
    E.add_spatial_feature(load_G)
    assert isinstance(E, Environment)

def test_environment_G_addition_correct(load_G):
    E = Environment()
    
    G = RoadNetworkGraph(load_G)
    E.add_spatial_feature(G)
    assert isinstance(E, Environment)

def test_environment_G_addition_name(load_G):
    E = Environment()

    G = RoadNetworkGraph(load_G)
    E.add_spatial_feature(G)
    assert E.spatial_data['RNG'].name == 'RNG'

# # Тесты профиля скоростей
# def test_SpeedProfile_creation():
#     '''Тест создания SpeedProfile'''
#     sp = SpeedProfile()
#     assert isinstance(sp, SpeedProfile)

# def test_SpeedProfile_default():
#     '''Тест создания SpeedProfile и указания значений по умолчанию'''
#     sp = SpeedProfile()
#     assert sp.sp["road"]==500

# def test_SpeedProfile_set_5():
#     '''Тест передачи в SpeedProfile скоростей для 5 типов дорог'''
#     sp = SpeedProfile()
#     sp.set_speeds_5([50,40,30,20,10])
#     assert sp.sp["living_street"]==500

# def test_SpeedProfile_precision():
#     '''Тест точности пересчета скоростей в км/ч'''
#     sp = SpeedProfile()
#     sp.kmh_to_mm_precision=0
#     sp.set_speeds_5([50,40,30,20,10])
#     assert sp.sp["corridor"]==167

# def test_SpeedProfile_set_speeds_from_dict():
#     '''Тест передачи в SpeedProfile скоростей согласно словарю'''
#     sp = SpeedProfile()
#     sp.set_speeds({
#         "secondary":60,
#         "service": 30,
#         "pedestrian":15
#     })
#     assert sp.sp["living_street"]==416.67

# @pytest.mark.xfail()
# def test_SpeedProfile_set_not_5():
#     '''Тест передачи в SpeedProfile скоростей для неверного количества типов дорог'''
#     sp = SpeedProfile()
#     sp.set_speeds_5([50,40,30,20])
#     assert sp.sp["living_street"]==500
