#%%
import geopandas as gpd
import osmnx as ox


#%%
poly = gpd.read_file('../tests/data/outter_borders.gpkg')
poly.plot()
# %%
tags = {'building': True}
fields = [
  'name',
  'amenity',
  'building',
  'addr:street',
  'addr:housenumber',
  'building:levels',
  'building:flats',
#   'rooms',
  'geometry',
]
buildings = ox.features_from_polygon(poly.geometry.unary_union, tags)
buildings = buildings[buildings.geometry.apply(lambda x: x.geom_type).isin(['Polygon', 'MultiPolygon'])]
buildings = buildings[fields]
buildings = buildings.reset_index().drop('element_type', axis=1)
buildings = buildings.set_index('osmid')
print('Набор зданий:', buildings.shape)

ax = poly.boundary.plot(color='r')
buildings.plot(ax=ax)

#%%
buildings.to_file('../tests/data/buildings.gpkg')
