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

#%% Загрузка сохраненных ранее зданий:
buildings = gpd.read_file('../tests/data/buildings.gpkg')
ax = poly.boundary.plot(color='r')
buildings.plot(ax=ax)

#%% Проверка по территориальному расположению
# Загрузка данных из OSM
tags = {'landuse':['residential',
                   'commercial',
                   'construction',
                   'education',
                   'industrial',
                   'residential',
                   'retail',
                   'institutional',
                   'allotments',
                   'brownfield'
                   ],
        'amenity':['prison']}
# landuses = ox.features.features_from_place(place, tags)
landuses = ox.features.features_from_polygon(poly.iloc[0].geometry, tags)
landuses = landuses[landuses.geometry.apply(lambda x: x.geom_type).isin(['Polygon', 'MultiPolygon'])]
landuses = landuses.reset_index().drop('element_type', axis=1).set_index('osmid')
print(landuses.shape)
landuses.plot()

#%% Исправление типов землепользования по полю `amenity`
for lid, data in landuses[landuses['amenity'].notna()].iterrows():
    landuses.loc[lid, 'landuse'] = data['amenity']

#%% Частная выборка для объединения
landuses_landuse = landuses[['landuse','name','amenity','geometry']].copy()

#%% Проверка нахождения наборов данных в единой системе координат
landuses_landuse = ox.project_gdf(landuses_landuse)
buildings = ox.project_gdf(buildings)
assert buildings.crs == landuses_landuse.crs


#%% Количество данных
buildings.groupby('building')['geometry'].count().sort_values(ascending = False)

#%% Список значений `building` нуждающихся в проверке
bldngs_need_for_check = [
 'yes',
]


#%% Дополнение данными
print('До:   ', len(buildings), len(buildings.query(f'building in {bldngs_need_for_check}')))

i=0
for bid, data in buildings.query(f'building in {bldngs_need_for_check}').iterrows():
    # print(bid)
    # if data['building'] in bldngs_need_for_check:
    print(i, end='\r')
    g = data['geometry']
    intersected = landuses_landuse[landuses_landuse.intersects(g)]
    if len(intersected)>=1:
        landuse = intersected.iloc[0]['landuse']
        buildings.loc[bid, 'building'] = landuse
    i+=1

print('')
print('После:   ', len(buildings), len(buildings.query(f'building in {bldngs_need_for_check}')))



#%% Переименовываем английские названия на русский язык
replace_list = (
    ('allotments', 'Дача'),    
    ('apartments', 'Многоквартирный жилой дом'),
    ('arts_centre', 'Музей'),
    ('barrack', 'Казармы'),
    ('brownfield', 'Заброшено'),    
    ('bus_station', 'Автовокзал'),    
    ('cafe', 'Здание общественного питания'),
    ('cathedral', 'Церковь'),    
    ('car_wash', 'Автомойка'),
    ('chapel', 'Церковь'),
    ('church', 'Церковь'),
    ('cinema', 'Кинотеатр'),
    ('civic', 'Общественное здание'),
    ('clinic', 'Больница'),
    ('college', 'Училище'),
    ('commercial', 'Коммерческое здание'),
    ('community_centre', 'Общественное здание'),
    ('construction', 'Строительство'),
    ('courthouse', 'Суд'),
    ('dentist', 'Больница'), 
    ('detached', 'Жилой дом'),        
    ('doctors', 'Больница'),
    ('dormitory', 'Общежитие'),
    ('fast_food', 'Здание общественного питания'),    
    ('fire_station', 'Пожарная часть'),
    ('fuel', 'АЗС'),
    ('garage', 'Гараж'),
    ('garages', 'Гараж'),
    ('government', 'Административное здание'),
    ('hangar', 'Ангар'),    
    ('hospital', 'Больница'),
    ('hotel', 'Гостиница'),
    ('house', 'Жилой дом'),
    ('houseboat', 'Жилой дом'),
    ('industrial', 'Производственное здание'),
    ('kindergarten', 'Детский сад'),
    ('kiosk', 'Киоск'),
    ('marketplace', 'Торговое здание'),
    ('mosque', 'Церковь'),    
    ('nightclub', 'Культурное учреждение'),    
    ('office', 'Административное здание'),
    ('parking', 'Парковка'),
    ('pavilion', 'Павильон'),
    ('pharmacy', 'Аптека'),
    ('place_of_worship', 'Церковь'),
    ('police', 'Административное здание'),
    ('post_office', 'Почта'),
    ('prison', 'Тюрьма'),    
    ('public', 'Общественное здание'),
    ('public_bath', 'Общественное здание'),
    ('rescue_station', 'Административное здание'),    
    ('residential', 'Многоквартирный жилой дом'),
    ('restaurant', 'Здание общественного питания'),    
    ('retail', 'Торговое здание'),
    ('roof', 'неизвестно'),    
    ('ruins', 'Заброшено'),
    ('school', 'Школа'),
    ('service', 'Служебная постройка'),
    ('shed', 'Сарай'),
    ('synagogue', 'Церковь'),    
    ('ship', 'Судно'),    
    ('shelter', 'неизвестно'),        
    ('social_facility', 'Общественное здание'),
    ('sports_centre', 'Спортивное сооружение'),    
    ('stadium', 'Спортивное сооружение'),
    ('storage_tank', 'Резервуар'),
    ('supermarket', 'Торговое здание'),
    ('temple', 'Церковь'),    
    ('theatre', 'Театр'),    
    ('townhall', 'Административное здание'),    
    ('training', 'Спортивное сооружение'),
    ('train_station', 'ЖД Вокзал'),    
    ('transformer_tower', 'Трансформатор'),
    ('toilets', 'неизвестно'),    
    ('university', 'ВУЗ'),
    ('warehouse', 'Склад'),
    ('yes', 'неизвестно'),    
    ('АГЗС', 'АЗС'),
    ('АЗС', 'АЗС'),
    ('Автомойка', 'Мастерская'),
    ('Автосалон', 'Автосалон'),
    ('Автосервис', 'Мастерская'),
    ('Автостоянка', 'Парковка'),
    ('Автоцентр', 'Автосалон'),
    ('Административное здание', 'Административное здание'),
    ('Апартаменты', 'Многоквартирный жилой дом'),
    ('Бани, сауны', 'Общественное здание'),
    ('Бизнес-центр', 'Торговое здание'),
    ('ВУЗ', 'ВУЗ'),
    ('Ветлечебница', 'Больница'),
    ('Гараж', 'Гараж'),
    ('Гипермаркет', 'Торговое здание'),
    ('Гостиница', 'Гостиница'),
    ('Детский дом', 'Детский дом'),
    ('Детский сад, ясли', 'Детский сад'),
    ('Жилой дом', 'Жилой дом'),
    ('Кафе, бар', 'Здание общественного питания'),
    ('Киоск', 'Киоск'),
    ('Коттедж', 'Жилой дом'),
    ('Культурное учреждение', 'Культурное учреждение'),
    ('Магазин', 'Торговое здание'),
    ('Малоэтажный жилой дом', 'Жилой дом'),
    ('Медицинское учреждение', 'Больница'),
    ('Музей', 'Музей'),
    ('Научное учреждение', 'Научное учреждение'),
    ('Общежитие', 'Общежитие'),
    ('Объект', 'неизвестно'),
    ('Парковка', 'Парковка'),
    ('Подземное сооружение', 'Подземное сооружение'),
    ('Производственный корпус', 'Производственное здание'),
    ('Прокат снаряжения', 'неизвестно'),
    ('Проходная, КПП', 'неизвестно'),
    ('Развлекательное заведение', 'Культурное учреждение'),
    ('Религиозное сооружение', 'Церковь'),
    ('Ремонтируемое здание', 'Строительство'),
    ('Ресторан', 'Здание общественного питания'),
    ('Склад', 'Склад'),
    ('Сооружение', 'неизвестно'),
    ('Спортивное сооружение', 'Спортивное сооружение'),
    ('Столовая', 'Здание общественного питания'),
    ('Строящееся административное здание', 'Строительство'),
    ('Строящееся здание', 'Строительство'),
    ('Строящийся жилой дом', 'Строительство'),
    ('Супермаркет', 'Торговое здание'),
    ('Таунхаус', 'Жилой дом'),
    ('Теплица', 'неизвестно'),
    ('Техникум, училище', 'Училище'),
    ('Торговый павильон', 'Торговое здание'),
    ('Торговый центр', 'Торговое здание'),
    ('Хозяйственный корпус', 'Административное здание'),
    ('Частный дом', 'Жилой дом'),
    ('Шиномонтаж', 'Мастерская'),
    ('Школа', 'Школа'),
    ('Школа-интернат', 'Школа'),
)

buildings['building'] = buildings['building'].fillna('неизвестно')
for d in replace_list:
    buildings['building'] = buildings['building'].replace(d[0], d[1])

buildings.groupby('building')['building'].count().sort_values(ascending=False)

# %%Перечень землепользования
landuses['landuse'].unique()

# %% Переименовываем землепользование
replace_list_lu = (
    ('industrial', 'Промышленное предприятие'),
    ('residential', 'Жилая застройка'),
    # ('retail', 'Торговая территория'),
    # ('brownfield', 'Заброшено'),
    ('allotments', 'Дачи'),
    ('prison', 'Тюрьма'),
    ('construction', 'Стройплощадка'),
    # ('marketplace', 'Торговая территория'),
    # ('commercial', 'Торговая территория'),
    # ('parking', 'Парковка'),
    # ('veterinary', 'Прочее'),
)
for d in replace_list_lu:
    landuses['landuse'] = landuses['landuse'].replace(d[0], d[1])

# %% Сохранение
# Здания:
ox.project_gdf(buildings, to_latlong=True).to_file('../tests/data/buildings.gpkg', layer='здания')
# Землепользование
ox.project_gdf(landuses, to_latlong=True)[['landuse','name','amenity','geometry','place']].to_file('../tests/data/landuse.gpkg', layer='землепользование')

# %% Таблица данных
buildings.query('building == "неизвестно"')
# %%
