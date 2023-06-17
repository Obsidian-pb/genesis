'''

pytest tests/test_models.py  
'''

import pytest

import osmnx as ox
# import networkx as nx
# import numpy as np

from genesis.models import Feature, SpatialFeature, Environment, RoadNetworkGraph, SpeedProfile
from genesis.tools import kmh_to_mm
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
        assert E.get['RNG'].name == 'RNG'

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

    def test_environment_add_and_load_features(self):
        RNG = RoadNetworkGraph(path = 'test_rng.ml')
        SP = SpeedProfile()
        E = Environment(path='tests/data/')
        E.add_spatial_feature(RNG).add_data_feature(SP)
        E.load()
        assert E.test()

    def test_environment_add_and_load_features_list(self):
        RNG = RoadNetworkGraph(path = 'test_rng.ml')
        SP = SpeedProfile()
        E = Environment(path='tests/data/')
        E.add_features([RNG, SP])
        E.load()
        assert E.test()


# Тесты профиля скоростей
class TestSP():
    def test_speed_profile_creation(self):
        '''Тест создания SpeedProfile'''
        sp = SpeedProfile()
        assert isinstance(sp, SpeedProfile)

    def test_speed_profile_load(self):
        '''Тест загрузки профиля скоростей'''
        sp = SpeedProfile().load(base_path='tests/data/')
        assert sp.get['primary'] == 40

    def test_speed_profile_def(self):
        '''Тест загрузки скоростей по-умолчанию'''
        sp = SpeedProfile()
        assert sp.get['secondary'] == 40
        assert sp.get['road'] == 30
        assert sp.get['living_street'] == 25
        assert sp.get['footway'] == 10
        assert sp.get['cycleway'] == 5


    def test_speed_profile_direct(self):
        '''Тест загрузки указанием при создании'''
        sp = SpeedProfile(speeds = [60, 50, 35, 15, 2])
        assert sp.get['secondary'] == 60
        assert sp.get['road'] == 50
        assert sp.get['living_street'] == 35
        assert sp.get['footway'] == 15
        assert sp.get['cycleway'] == 2

    def test_speed_profile_get_by_name(self):
        '''Тест получения скорости для типа дорог'''
        sp = SpeedProfile().load(base_path='tests/data/')
        assert sp['trunk'] == round(40 * 1000 / 60, 2)

    @pytest.mark.xfail()
    def test_speed_profile_load_by_wrong_path(self):
        sp = SpeedProfile().load()
        assert sp['trunk'] == round(40 * 1000 / 60, 2)

    def test_speed_profile_check_highway_count(self):
        sp = SpeedProfile().load(base_path='tests/data/')
        assert len(sp.get) == 23

    def test_speed_profile_save(self, tmp_path_factory):
        sp = SpeedProfile().load(base_path='tests/data/')
        tmp_path = tmp_path_factory.mktemp("tests") / "test_sp.yml"
        sp.path = tmp_path
        sp.save()
        assert isinstance(sp, SpeedProfile)

    def test_test(self):
        sp = SpeedProfile().load(base_path='tests/data/')
        assert sp.test()

    def test_speed_profile_set_speeds(self):
        '''Установка скоростей движения для 5 
        преднастроенных в SP групп дорог
        '''
        sp = SpeedProfile()
        speeds_list = [60, 50, 35, 15, 2]
        sp._set_speeds(
            speeds = speeds_list
        )
        assert sp['secondary'] == kmh_to_mm(speeds_list[0])
        assert sp['road'] == kmh_to_mm(speeds_list[1])
        assert sp['living_street'] == kmh_to_mm(speeds_list[2])
        assert sp['footway'] == kmh_to_mm(speeds_list[3])
        assert sp['cycleway'] == kmh_to_mm(speeds_list[4])

    def test_speed_profile_set_speeds_correct(self):
        sp = SpeedProfile()
        sp._set_speeds(
            speeds=[50,40,30,20,10],
            def_highways=[
                ["motorway", "motorway_link", "trunk", "trunk_link", "primary", 
                "primary_link", "secondary", "secondary_link"],
                ["road", "unclassified", "tertiary", "tertiary_link"],
                ["living_street", "service", "residential", "track"],
                ["footway", "path", "pedestrian"],
                ["steps", "cycleway", "bridleway", "corridor"]
            ]
        )
        assert sp.test()
        assert sp.get['steps'] == 10

    def test_speed_profile_set_speeds_correct_6(self):
        sp = SpeedProfile()
        sp._set_speeds(
            speeds=[50,40,30,20,10,5],
            def_highways=[
                ["motorway", "motorway_link", "trunk", "trunk_link", "primary", 
                "primary_link", "secondary", "secondary_link"],
                ["road", "unclassified", "tertiary", "tertiary_link"],
                ["living_street", "service", "residential", "track"],
                ["footway", "path", "pedestrian"],
                ["steps", "cycleway"],
                ["bridleway", "corridor"]
            ]
        )
        assert sp.test()
        assert sp.get['corridor'] == 5

    @pytest.mark.xfail()
    def test_speed_profile_set_speeds_wrong(self):
        sp = SpeedProfile()
        sp._set_speeds(
            speeds=[50,40,30,20],
            def_highways=[
                ["motorway", "motorway_link", "trunk", "trunk_link", "primary", 
                "primary_link", "secondary", "secondary_link"],
                ["road", "unclassified", "tertiary", "tertiary_link"],
                ["living_street", "service", "residential", "track"],
                ["footway", "path", "pedestrian"],
                ["steps", "cycleway", "bridleway", "corridor"]
            ]
        )
        assert sp.test()



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