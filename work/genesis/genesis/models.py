'''
Модели используемые в расчетах
'''

import pandas as pd
import networkx as nx
import osmnx as ox
# import yaml
from shapely.geometry import MultiPolygon, Polygon

# from genesis.tools import kmh_to_mm
from genesis.interfaces import IFeature, IEnvironment, ISpatialFeature, IModel, IDataFeature


class Environment(IEnvironment, IFeature, ISpatialFeature):        # Это уже реализация!!!
    '''
    Базовая реализация модели окружения. 
    В нее входит ГДС, размещение подразделений, объектов, и т.д.
    '''
    class DataVault: pass
    spatial_data = DataVault()
    data = DataVault()

    def __init__(self, name: str = 'E_Base', path: str = '') -> None:
        self.name=name
        self.path=path

    def add_spatial_feature(self, spatial_feature: ISpatialFeature, **attr):
        '''
        Добавление пространственных данных
        
        Аргументы
        ---------
        `spatial_feature`: ISpatialFeature
            Пространственные данные.
            Могут быть любым типом пространственных данных.
            Но наиболее распространенные - gpd.GeoDataFrame и
            nx.MultiDiGraph. Для передачи в функцию он должны
            реализовывать интерфейс ISpatialFeature

        Возвращает
        ----------
        `self`: Environment
            Ссылка на самого себя
        '''

        if not isinstance(spatial_feature, IFeature):
            raise TypeError("аргумент 'spatial_feature' должен \
                            реализовывать интерфейс 'IFeature'!")
        if not isinstance(spatial_feature, ISpatialFeature):
            raise TypeError("аргумент 'spatial_feature' должен \
                            реализовывать интерфейс 'ISpatialFeature'")

        # self.spatial_data[spatial_feature.name] = spatial_feature
        setattr(self.spatial_data, spatial_feature.name, spatial_feature)
        return self

    def add_data(self, data: pd.DataFrame, **attr):
        '''
        Добавление непространственных данных

        Аргументы
        ---------
        `data`: pd.DataFrame
            Датафрайм данных

        Возвращает
        ----------
        `self`: Environment
            Ссылка на самого себя
        '''

        if not isinstance(data, pd.DataFrame):
            raise TypeError("Аргумент 'data' должен \
                            иметь тип данных 'pd.DataFrame'!")
        if data.name=='':
            raise NameError("Для аргумента 'data' \
                            не указано имя!")
        setattr(self.data, data.name, data)
        return self

    def frame(self, polygon: Polygon | MultiPolygon, feature_names:list=None, **attr):
        '''
        Получение фрагмента Окружения
        
        Аргументы
        ---------
        `polygon`: Polygon | MultiPolygon
            Полигон или мультиполигон которым следует обрезать
            пространственные данные
        `feature_names`: list
            Список имен пространственных данных. 
            Если указан, происходит выбор данных только для
            указанных наборов. 
            Иначе для всех наборов пространственных данных.
        '''

    def load(self, **attr):
        '''Загрузка модели'''

    def save(self, **attr):
        '''Сохранение модели'''

    def test(self):
        '''Проверить корректность модели'''

    @property
    def name(self):
        '''Имя набора данных'''
        return self._name
    @name.setter
    def name(self, name):
        self._name=name

    @property
    def path(self):
        '''Путь к файлу на диске'''
        return self._path
    @path.setter
    def path(self, path):
        self._path=path




class Model(IModel):                    # Это уже реализация!!!
    '''
    Базовая реализация расчетной модели
    '''


class RoadNetworkGraph(nx.MultiDiGraph, IFeature, ISpatialFeature):
    '''
    Граф дорожной сети.
    '''
    def __init__(self, incoming_graph_data=None, multigraph_input=None, 
                 name='RNG', path='data/rng.ml',
                 **attr):
        self.path=path
        self.name=name
        super().__init__(incoming_graph_data, multigraph_input, **attr)


    def frame(self, polygon: Polygon, **attr):
        return ox.truncate.truncate_graph_polygon(self, polygon, **attr)
    
    def load(self):
        '''Загрузка из файла-источника'''
        self = RoadNetworkGraph(ox.load_graphml(self.path))

    def save(self):
        '''Сохранение в файл-источник'''
        ox.save_graphml(self, self.path)

    def test(self):
        '''Проверить корректность данных'''
        print(str(self))


    @property
    def name(self):
        '''Имя набора данных'''
        return self._name
    @name.setter
    def name(self, name):
        self._name=name

    @property
    def path(self):
        '''Путь к файлу на диске'''
        return self._path
    @path.setter
    def path(self, path):
        self._path=path



# class SpeedProfile(pd.DataFrame, IFeature, IDataFeature):
#     '''
#     Профиль скоростей
#     '''
#     def __init__(self, name='SP', path='data/speeds.yml',
#                  **attr):
#         self.path=path
#         self.name=name
#         super().__init__(**attr)


    
#     def load(self):
#         '''Загрузка из файла-источника'''
#         with open(self.path, 'r') as file:
#             data = yaml.load(file, Loader=yaml.FullLoader)
#         pd.DataFrame.from_dict(data)

#     def save(self):
#         '''Сохранение в файл-источник'''
#         ox.save_graphml(self, self.path)

#     def test(self):
#         '''Проверить корректность данных'''
#         print(str(self))


#     @property
#     def name(self):
#         '''Имя набора данных'''
#         return self._name
#     @name.setter
#     def name(self, name):
#         self._name=name

#     @property
#     def path(self):
#         '''Путь к файлу на диске'''
#         return self._path
#     @path.setter
#     def path(self, path):
#         self._path=path







# # Переделать
# class SpeedProfile(object):
#     '''
#     Модель профиля скоростей движения техники по различным типам поверхностей
#     '''

#     def __init__(self, precision=2):
#         self._sp = {}
#         self.kmh_to_mm_precision = precision
#         # первоначальная инициализация
#         self.set_speeds_5([40,30,25,10,5])

#     def set_speeds(self, speeds:dict):
#         '''
#         Устанавливает скорости движения для всех типов улиц,
#         переданных в соответствии с аргументом.

#         Важно! Скорость указывается только в км/ч

#         Аргументы
#         ---------

#         `speeds`:dict
#             Словарь скоростей движения по различным типам улиц.
#             В словаре ключ - наименование типа улицы,
#             значение - скорость движения по каждому из типов улиц
        
#         Пример
#         ------
#         sp = SP()
#         sp.set_speeds_all(
#             {"motorway":40,
#                 "trunk":35
#             }
#         )
#         '''
#         if not isinstance(speeds, dict):
#             raise TypeError("Аргумент speeds должен быть только типа dict!")

#         for k,v in speeds.items():
#             self._sp[k]=v

#     def set_speeds_5(self, speeds:list):
#         '''
#         Устанавливает скорости движения для всех типов улиц,
#         переданных в соответствии с аргументом. При этом типы дорог разбиты
#         на 5 групп.

#         Важно! Скорость указывается только в км/ч

#         Аргументы
#         ---------
#         speeds: list
#             Список 5 скоростей в км/ч

#             1 - наиболее крупные автомагистрали
#                 ["motorway", "motorway_link", "trunk", "trunk_link", "primary", 
#                 "primary_link", "secondary", "secondary_link"]

#             2 - остальные дороги: служебные проезды:, внутриквартальные,
#             въездные, парковочные
#                 ["road", "unclassified", "tertiary", "tertiary_link"]
            
#             3 - Жилые зоны и дворовые проезды
#                 ["living_street", "service", "residential", "track"]

#             4 - Пешеходные дорожки, тротуары и прочие пригодные
#             для движения автомобилей
#                 ["footway", "path", "pedestrian"]

#             5 - области не являющиеся дорогами, но теоретически пригодные
#             для перемещения пожарной техники
#                 ["steps", "cycleway", "bridleway", "corridor"]

#             Более подробно о типах дорог можно прочесть здесь: 
#         '''
#         if not isinstance(speeds, list):
#             raise TypeError("Аргумент speeds должен быть только типа list!")
#         if len(speeds)!=5:
#             raise ValueError('Список скоростей должен состоять строго из 5 значений!')

#         s_1, s_2, s_3, s_4, s_5 = speeds
#         speeds_dict = {
#             # Автомагистрали
#             "motorway":       s_1,
#             "motorway_link":  s_1,
#             # Важные дороги, не являющиеся автомагистралями
#             "trunk":          s_1,
#             "trunk_link":     s_1,
#             # Автомобильные дороги регионального значения
#             "primary":        s_1,
#             "primary_link":   s_1,
#             # Автомобильные дороги областного значения
#             "secondary":      s_1,
#             "secondary_link": s_1,

#             # Более важные автомобильные дороги среди прочих
#             # автомобильных дорог местного значения
#             "tertiary":       s_2,
#             "tertiary_link":  s_2,
#             # Линии, возможно, являющиеся дорогами. Временный тег,
#             # которым следует помечать линии до уточнения.
#             "road":           s_2,
#             # Остальные автомобильные дороги местного значения,
#             # образующие соединительную сеть дорог.
#             "unclassified":   s_2,

#             # Служебные проезды: внутриквартальные, въездные, парковочные и т.д.
#             "service":        s_3,
#             # Дороги, которые проходят внутри жилых зон, а также используются
#             # для подъезда к ним
#             "residential":    s_3,
#             # Жилые зоны и дворовые проезды
#             "living_street":  s_3,
#             # Дороги сельскохозяйственного назначения, лесные дороги,
#             # не ведущие к жилым или промышленным объектам,
#             # неофициальные грунтовки, козьи тропы
#             "track":          s_3,           

#             # Пешеходные дорожки, тротуары.
#             "footway":        s_4,           
#             # Тропа (чаще всего, стихийная) использующаяся пешеходами,
#             # либо одним или несколькими видами транспорта,
#             # кроме четырехколесного (лыжи, снегоход, велосипед).
#             "path":           s_4,
#             # Для обозначения улиц городов (такого же класса как residential),
#             # выделенных для пешеходов.
#             "pedestrian":     s_4,

#             # Лестницы, лестничные пролёты
#             "steps":          s_5,
#             # Велодорожка, обозначенная соответствующим дорожным знаком
#             "cycleway":       s_5,
#             # Дорожки для верховой езды.
#             "bridleway":      s_5,
#             # Коридоры внутри крупных зданий
#             "corridor":       s_5,
#         }
#         self.set_speeds(speeds_dict)

#     @property
#     def sp(self):
#         '''
#         Текущий профиль скоростей
#         '''
#         return {k: kmh_to_mm(v, precision=self.kmh_to_mm_precision) for k,v in self._sp.items()}


