#%% Тестирование функции net_overlay
import osmnx as ox
import networkx as nx

from graphs.algorithms import generate_grid_graph, net_overlay

print(ox.__version__)

#%% Генерируем граф
G = generate_grid_graph(n=100, m=100, step=100.0, speed=30.0)
nx.set_edge_attributes(G, 'undefined', 'highway')


#%%
g_nodes = ox.graph_to_gdfs(G, edges=False)
key_nodes = g_nodes.sample(3)

GN = net_overlay(G, list(key_nodes.index), cutoff=5000)
gn_edges = ox.graph_to_gdfs(GN, nodes=False)
# Указываем aspect=1 для корректного отображения проецированных координат
gn_edges.plot(aspect=1)