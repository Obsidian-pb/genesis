'''

pytest tests/test_models.py  
'''

import pytest

import osmnx as ox
import geopandas as gpd
# import networkx as nx
# import numpy as np

from genesis.models import Feature
from genesis.models import SpatialFeature
from genesis.models import Environment
from genesis.models import RoadNetworkGraph
from genesis.models import SpeedProfile
from genesis.models import DislocationProfile

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
        RNG = RoadNetworkGraph(load_G)
        assert isinstance(RNG, RoadNetworkGraph)
        assert isinstance(RNG, SpatialFeature)
        assert isinstance(RNG, Feature)

    def test_RNG_props(self, load_G):
        RNG = RoadNetworkGraph(load_G)
        assert 'RNG'==RNG.name
        assert 'rng.ml'==RNG.path

    def test_RNG_props_set(self, load_G):
        RNG = RoadNetworkGraph(load_G)
        RNG.name = 'rng'
        RNG.path = 'data/new.ml'
        assert 'rng'==RNG.name
        assert 'data/new.ml'==RNG.path

    def test_RNG_load(self):
        RNG = RoadNetworkGraph(path='tests/data/test_rng.ml')
        RNG.load()
        assert RNG.get.number_of_nodes() > 100

    @pytest.fixture(scope="session")
    def ml_file(self, tmp_path_factory):
        g = ox.load_graphml("tests/data/test_rng.ml")
        tmp_path = tmp_path_factory.mktemp("tests") / "test_rng2.ml"
        RNG = RoadNetworkGraph(g, path=tmp_path)
        RNG.save()
        return tmp_path

    def test_RNG_load_tmp(self, ml_file):
        RNG = RoadNetworkGraph(path=ml_file)
        RNG.load()
        assert isinstance(RNG, RoadNetworkGraph)

    def test_RNG_crs(self, load_G):
        RNG = RoadNetworkGraph(load_G)
        assert 'epsg:4326' == RNG.crs
        new_crs='epsg:3857'
        RNG.crs = new_crs
        assert new_crs == RNG.crs

    @pytest.mark.xfail()
    def test_RNG_no_data(self):
        RNG = RoadNetworkGraph()
        return RNG.test()


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
        assert E.RNG.name == 'RNG'

    def test_environment_G_load(self):
        E = Environment()
        RNG = RoadNetworkGraph(path='tests/data/test_rng.ml')
        E.add_spatial_feature(RNG)
        E.load()
        assert E['RNG'].get.number_of_nodes()>0

    @pytest.mark.xfail()
    def test_environment_feature_wo_load(self):
        E = Environment()
        RNG = RoadNetworkGraph(path='tests/data/test_rng.ml')
        E.add_spatial_feature(RNG)
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

    def test_environment_set_crs(self):
        E = Environment(path='tests/data/')
        E.add_features(
            [
                RoadNetworkGraph(path='test_rng.ml'),
                DislocationProfile(),
                SpeedProfile()
            ]
        )
        E.load()
        E.crs = 'epsg:4326'
        assert E.crs == 'epsg:4326'
        assert E.RNG.crs == 'epsg:4326'
        assert E.DP.crs == 'epsg:4326'
        E.crs = 'epsg:3857'
        assert E.crs == 'epsg:3857'
        assert E.RNG.crs == 'epsg:3857'
        assert E.DP.crs == 'epsg:3857'

    def test_environment_add_features_in_init(self):
        E = Environment(spatial_data = [
                RoadNetworkGraph(path='test_rng.ml'),
                DislocationProfile(),
                SpeedProfile()
            ],
            path='tests/data/')
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



# === Тесты DislocationProfile
@pytest.fixture()
def load_dp_data():
    return gpd.read_file('tests/data/stations.gpkg')

class TestDislocationProfile():
    def test_dp_creation(self):
        DP = DislocationProfile()
        assert isinstance(DP, DislocationProfile)

    def test_dp_creation_by_geodataframe(self, load_dp_data):
        DP = DislocationProfile(load_dp_data)
        assert isinstance(DP.data, gpd.GeoDataFrame)
        assert len(DP.data)==2

    def test_dp_load_from_file(self):
        DP = DislocationProfile().load(base_path='tests/data/')
        assert len(DP.data)==2

    def test_dp_get_station_by_name(self):
        DP = DislocationProfile().load(base_path='tests/data/')
        station_name = 'ПСЧ-1'
        assert DP.data.loc[station_name, 'type']=='ФПС'
        assert DP[station_name]['type'] == 'ФПС'

    def test_dp_crs(self, load_dp_data):
        DP = DislocationProfile(load_dp_data)
        assert 'epsg:3857' == DP.crs
        new_crs='epsg:4326'
        DP.crs = new_crs
        assert new_crs == DP.crs

    @pytest.mark.xfail()
    def test_dp_no_data(self):
        DP = DislocationProfile()
        return DP.test()




# === Тесты UnitsState




# === Тесты ObjectsState
