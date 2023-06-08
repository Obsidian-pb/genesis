import pytest

import osmnx as ox
# import networkx as nx
# import numpy as np

from genesis.models import Environment
from genesis.models import SpeedProfile

@pytest.fixture()
def load_G():
    return ox.load_graphml("tests/data/test_rng.ml")

def test_environment_creation(load_G):
    E = Environment(load_G)
    assert isinstance(E, Environment)


# Тесты профиля скоростей
def test_SpeedProfile_creation():
    '''Тест создания SpeedProfile'''
    sp = SpeedProfile()
    assert isinstance(sp, SpeedProfile)

def test_SpeedProfile_default():
    '''Тест создания SpeedProfile и указания значений по умолчанию'''
    sp = SpeedProfile()
    assert sp.sp["road"]==500

def test_SpeedProfile_set_5():
    '''Тест передачи в SpeedProfile скоростей для 5 типов дорог'''
    sp = SpeedProfile()
    sp.set_speeds_5([50,40,30,20,10])
    assert sp.sp["living_street"]==500

def test_SpeedProfile_precision():
    '''Тест точности пересчета скоростей в км/ч'''
    sp = SpeedProfile()
    sp.kmh_to_mm_precision=0
    sp.set_speeds_5([50,40,30,20,10])
    assert sp.sp["corridor"]==167

def test_SpeedProfile_set_speeds_from_dict():
    '''Тест передачи в SpeedProfile скоростей согласно словарю'''
    sp = SpeedProfile()
    sp.set_speeds({
        "secondary":60,
        "service": 30,
        "pedestrian":15
    })
    assert sp.sp["living_street"]==500

@pytest.mark.xfail()
def test_SpeedProfile_set_not_5():
    '''Тест передачи в SpeedProfile скоростей для неверного количества типов дорог'''
    sp = SpeedProfile()
    sp.set_speeds_5([50,40,30,20])
    assert sp.sp["living_street"]==500