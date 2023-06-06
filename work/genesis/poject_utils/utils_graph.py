#%%
import osmnx as ox
import geopandas as gpd

#%%
PLACE = "Сосновоборск, Красноярский край, Россия"

# Полигон населенного пункта
gdf = ox.geocode_to_gdf(PLACE)
ox.plot_footprints(gdf)

#%% Сохранение
gdf.to_file('G:/GitRepositories/_Dislocation/genesis/work/genesis/tests/data/test_polygon.gpkg', 
            driver="GPKG", 
            encoding='UTF-8')

#%% Граф дорожной сети
G = ox.graph_from_place(PLACE, 
                          simplify=False,
                          retain_all=True,
                          buffer_dist=1000)
ox.plot_graph(G, node_size=0)

#%%
ox.save_graphml(G, "G:/GitRepositories/_Dislocation/genesis/work/genesis/tests/data/test_rng.ml")
ox.save_graph_geopackage(G, "G:/GitRepositories/_Dislocation/genesis/work/genesis/tests/data/test_rng.gpkg")


# %%
