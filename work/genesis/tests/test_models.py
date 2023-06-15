'''

pytest tests/test_models.py  
'''

import pytest

import osmnx as ox
# import networkx as nx
# import numpy as np

from genesis.models import Feature, SpatialFeature, Environment, RoadNetworkGraph, SpeedProfile
# from genesis.interfaces import IFeature, ISpatialFeature
# from genesis.models import SpeedProfile

@pytest.fixture()
def load_G():
    return ox.load_graphml("tests/data/test_rng.ml")

@pytest.fixture()
def load_E():
    E = Environment()
    RNG = RoadNetworkGraph(path="tests/data/test_rng.ml")
    E.add_spatial_feature(RNG)
    E.load()
    return E

# === Тесты RoadNetworkGraph
class TestRNG():
    '''
    Тесты работы с RoadNetworkGraph
    '''
    def test_RNG_creation(self, load_G):
        G = RoadNetworkGraph(load_G)
        assert isinstance(G, RoadNetworkGraph)
        assert isinstance(G, SpatialFeature)
        assert isinstance(G, Feature)

    def test_RNG_props(self, load_G):
        G = RoadNetworkGraph(load_G)
        assert 'RNG'==G.name
        assert 'rng.ml'==G.path

    def test_RNG_props_set(self, load_G):
        G = RoadNetworkGraph(load_G)
        G.name = 'rng'
        G.path = 'data/new.ml'
        assert 'rng'==G.name
        assert 'data/new.ml'==G.path

    def test_RNG_load(self):
        RNG = RoadNetworkGraph(path='tests/data/test_rng.ml')
        RNG.load()
        assert RNG.get.number_of_nodes() > 100

    @pytest.fixture(scope="session")
    def ml_file(self, tmp_path_factory):
        g = ox.load_graphml("tests/data/test_rng.ml")
        tmp_path = tmp_path_factory.mktemp("tests") / "test_rng2.ml"
        G = RoadNetworkGraph(g, path=tmp_path)
        G.save()
        return tmp_path

    def test_RNG_load_tmp(self, ml_file):
        G = RoadNetworkGraph(path=ml_file)
        G.load()
        assert isinstance(G, RoadNetworkGraph)



# === Тесты DataFeature




# === Тесты Environment
class TestEnvironment():
    '''
    Тесты работы с RoadNetworkGraph
    '''
    def test_environment_creation(self):
        E = Environment()
        assert isinstance(E, Environment)

    def test_environment_name(self):
        E = Environment()
        assert E.name == 'E_Base'

    @pytest.mark.xfail()
    def test_environment_G_addition_wrong(self, load_G):
        E = Environment()
        E.add_spatial_feature(load_G)
        assert isinstance(E, Environment)

    def test_environment_G_addition_correct(self, load_G):
        E = Environment()
        RNG = RoadNetworkGraph(load_G)
        E.add_spatial_feature(RNG)
        assert isinstance(E, Environment)

    def test_environment_G_addition_name(self, load_G):
        E = Environment()
        RNG = RoadNetworkGraph(load_G)
        E.add_spatial_feature(RNG)
        assert E['RNG'].name == 'RNG'

    def test_environment_G_load(self):
        E = Environment()
        RNG = RoadNetworkGraph(path='tests/data/test_rng.ml')
        E.add_spatial_feature(RNG)
        E.load()
        assert E['RNG'].get.number_of_nodes()>0

    @pytest.fixture(scope="session")
    def env_file(self, tmp_path_factory):
        g = ox.load_graphml("tests/data/test_rng.ml")
        tmp_path = tmp_path_factory.mktemp("tests") / "test_rng2.ml"
        RNG = RoadNetworkGraph(g, path=tmp_path)
        E = Environment()
        E.add_spatial_feature(RNG)
        E.save()
        return tmp_path

    def test_RNG_load_tmp(self, env_file):
        RNG = RoadNetworkGraph(path=env_file)
        E = Environment()
        E.add_spatial_feature(RNG)
        E.load()
        assert E['RNG'].get.number_of_nodes()>0

    def test_environment_get_G_by_name(self, load_E):
        E = load_E
        assert isinstance(E['RNG'], RoadNetworkGraph)
        assert isinstance(E.RNG, RoadNetworkGraph)
        assert E.RNG.get.number_of_nodes()>0


# Тесты профиля скоростей
class TestSP():
    def test_speed_profile_creation(self):
        '''Тест создания SpeedProfile'''
        sp = SpeedProfile()
        assert isinstance(sp, SpeedProfile)

    def test_speed_profile_load(self):
        '''Тест загрузки профиля скоростей'''
        sp = SpeedProfile().load(base_path='tests/data/')
        assert sp.get['primary'] == 30

    def test_speed_profile_get_by_name(self):
        '''Тест получения скорости для типа дорог'''
        sp = SpeedProfile().load(base_path='tests/data/')
        assert sp['trunk'] == round(40 * 1000 / 60, 2)
        


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



# === Тесты StationsState
 






# === Тесты UnitsState




# === Тесты ObjectsState