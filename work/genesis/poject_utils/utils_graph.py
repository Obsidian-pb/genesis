#%%
import osmnx as ox
import geopandas as gpd

#%%
PLACE = "Сосновоборск, Красноярский край, Россия"

#%% Полигон населенного пункта
gdf = ox.geocode_to_gdf(PLACE)
ox.plot_footprints(gdf)

# Сохранение
gdf.to_file('G:/GitRepositories/_Dislocation/genesis/work/genesis/tests/data/test_polygon.gpkg', 
            driver="GPKG", 
            encoding='UTF-8')

#%% Граф дорожной сети
G = ox.graph_from_place(PLACE, 
                          simplify=False,
                          retain_all=True,
                          buffer_dist=2000)
ox.plot_graph(G, node_size=0)

#%%
ox.save_graphml(G, "G:/GitRepositories/_Dislocation/genesis/work/genesis/tests/data/test_rng.ml")
ox.save_graph_geopackage(G, "G:/GitRepositories/_Dislocation/genesis/work/genesis/tests/data/test_rng.gpkg")





# %% Параметры тестового графа
import osmnx as ox
import geopandas as gpd
import networkx as nx
import numpy as np
import pandas as pd

def kmh_to_mm(kmh):
    '''
    Перевод километров в час в метры в минуту
    '''
    return kmh*1000/60

# G = ox.load_graphml("G:/GitRepositories/_Dislocation/genesis/work/genesis/tests/data/test_rng.ml")

hwy_speeds = {
    'secondary': 35,
    'service': 30,
    'tertiary': 35,
    'unclassified': 30,
    'residential': 20,
    'track': 40,
    'footway': 5,
    'path': 5,
    'steps': 5,
    'road': 30,
    'secondary_link': 35    
}
hwy_speeds = {k: kmh_to_mm(v) for k,v in hwy_speeds.items()}

# ox.add_edge_speeds(G, 
#                    precision=2,
#                    hwy_speeds=hwy_speeds)

# ox.add_edge_travel_times(G, precision=2)

# edges = ox.graph_to_gdfs(G, nodes=False)

defSpeed=5
for edge in G.edges:
    road = G.get_edge_data(*edge).get('highway')
    length = G.get_edge_data(*edge).get('length')
    try:
        speed = hwy_speeds.get(road, defSpeed)
    except TypeError: # Тип дороги бывает списком, обычно ['residential', 'сервис']
        if isinstance(road, list):
            speed = hwy_speeds.get(road, defSpeed)
        else:
            speed = defSpeed

    G.add_edge(*edge, travel_time=length/speed)



#%%
node = list(G.nodes())[2000]
nc = ['r' if nd == node else 'w' for nd in G.nodes()]
ns = [10 if nd == node else 0 for nd in G.nodes()]
ox.plot_graph(G,
              node_color=nc,
              node_size=ns)

# %%
route_lens = nx.single_source_dijkstra_path_length(
    G, 
    node, 
    weight='travel_time')
route_lens_s = pd.Series(route_lens)

results = {}
results['max'] = np.max(route_lens_s)
results['mean'] = np.mean(route_lens_s)
results['median'] = np.median(route_lens_s)

covered_10 = [1 if t<=(10) else 0 for t in route_lens.values()]
covered_20 = [1 if t<=(20) else 0 for t in route_lens.values()]

results['ip10'] = round(100*sum(covered_10)/len(covered_10), 2)
results['ip20'] = round(100*sum(covered_20)/len(covered_20), 2)

results

#%%
ox.save_graphml(G, "G:/GitRepositories/_Dislocation/genesis/work/genesis/tests/data/test_rng.ml")
ox.save_graph_geopackage(G, "G:/GitRepositories/_Dislocation/genesis/work/genesis/tests/data/test_rng.gpkg")


# %%
G = ox.graph_from_place(PLACE, 
                          simplify=True,
                          retain_all=True,
                          buffer_dist=2000)
edges = ox.graph_to_gdfs(G, nodes=False)
edges.columns
# %%
