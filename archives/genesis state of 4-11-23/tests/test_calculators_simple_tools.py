'''
Тесты простых инструментальных функция модуля `calculators.py`
'''

import pytest

from genesis.tools import kmh_to_mm, data_frame_to_geo_data_frame
import pandas as pd
import geopandas as gpd
import osmnx as ox

def test_kmh_to_mm():
    kmh = 30
    assert kmh_to_mm(kmh)==500

@pytest.mark.xfail()
def test_kmh_to_mm_wrong_data_type():
    kmh = '30'
    assert kmh_to_mm(kmh)==500

class TestDFtoGDF():
    def test_data_frame_to_geo_data_frame(self):
        df = pd.read_csv('tests/data/ap_df.csv')
        G = ox.load_graphml("tests/data/test_rng.ml")
        nodes_gdf = ox.graph_to_gdfs(G, edges=False)
        gdf = data_frame_to_geo_data_frame(df, nodes_gdf)
        assert isinstance(gdf, gpd.GeoDataFrame)
        assert gdf.index.name == 'node'

