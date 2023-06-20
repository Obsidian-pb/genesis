'''
Тесты морферов
'''
import pytest

from genesis.models import SpatialFeature, RoadNetworkGraph, DislocationProfile
from genesis.morphers import MorphersSpatialFeature


class TestMorphersDP():
    def test_add_nearest_node(self):
        base_path = 'tests/data/'
        RNG = RoadNetworkGraph(path = 'test_rng.ml').load(base_path)
        DP = DislocationProfile().load(base_path)
        DP.crs = RNG.crs

        MorphersSpatialFeature.add_nearest_node(DP, RNG)
        assert 'node' in DP.data.columns
        assert len(DP.data)==2
        assert DP['ОП ПСЧ-1']['node'] == 4116050007

    def test_add_nearest_node_far_nodes(self):
        base_path = 'tests/data/'
        RNG = RoadNetworkGraph(path = 'test_rng.ml').load(base_path)
        DP = DislocationProfile().load(base_path)
        DP.crs = RNG.crs

        MorphersSpatialFeature.add_nearest_node(DP, RNG, max_dist=10)
        assert len(DP.data)==0

    def test_add_nearest_node_change_field(self):
        base_path = 'tests/data/'
        RNG = RoadNetworkGraph(path = 'test_rng.ml').load(base_path)
        DP = DislocationProfile().load(base_path)
        DP.crs = RNG.crs

        MorphersSpatialFeature.add_nearest_node(DP, RNG, node_field='nf')
        assert DP['ОП ПСЧ-1']['nf'] == 4116050007

    @pytest.mark.xfail()
    def test_add_nearest_node_wrong_crs(self, base_path = 'tests/data/'):
        RNG = RoadNetworkGraph(path = 'test_rng.ml').load(base_path)
        DP = DislocationProfile().load(base_path)

        MorphersSpatialFeature.add_nearest_node(DP, RNG)
        assert 'node' in DP.data.columns

    @pytest.mark.xfail()
    def test_add_nearest_node_wrong_data(self, base_path = 'tests/data/'):
        RNG = RoadNetworkGraph(path = 'test_rng.ml').load(base_path)
        DP = DislocationProfile().load(base_path)
        MorphersSpatialFeature.add_nearest_node(DP, DP)
        assert 'node' in DP.data.columns
        MorphersSpatialFeature.add_nearest_node(RNG, RNG)
        assert 'node' in DP.data.columns
