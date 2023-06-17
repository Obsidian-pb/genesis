'''
Модели используемые в расчетах
'''

from abc import abstractmethod
from typing import Any

import pandas as pd
import networkx as nx
import osmnx as ox
import yaml
from shapely.geometry import MultiPolygon, Polygon

# from genesis.tools import kmh_to_mm
from genesis.interfaces import IFeature, IEnvironment, ISpatialFeature, IModel, IDataFeature
from genesis.tools import kmh_to_mm

class Feature(object):
    '''
    Базовый класс данных модели
    '''
    _path=''
    _name=''
    _data=None

    def __init__(self,
                 name='', path='',
                 **attr):
        self.path=path
        self.name=name

    @abstractmethod
    def load(self, base_path='', **attr):
        '''Загрузка из файла-источника'''

    @abstractmethod
    def save(self, base_path='', **attr):
        '''Сохранение в файл-источник'''

    # @property
    # @abstractmethod
    # def get(self):
    #     '''Возвращает данные'''

    @abstractmethod
    def test(self):
        '''Проверить корректность данных'''

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

    @property
    def get(self):
        '''Вовзращает данные модели'''
        return self._data
    
    @property
    def version(self):
        '''Версия реализации модели.
        Рекомендуется указывать в формате `*.*.*`
        Рекомендуется указывать только для рабочих
        реализаций классов - например, для `RoadNetworkGraph`,
        но не для `SpatialFeature`'''
        return 'Для данной реализации версия не указана'


class SpatialFeature(Feature):
    '''
    Класс пространственных данных
    '''

    def __init__(self, spatial_data,
                 name='', path='', **attr):
        self._data = spatial_data
        super().__init__(name, path, **attr)

    @abstractmethod
    def frame(self, polygon: Polygon | MultiPolygon, **attr):
        '''
        Представление данных в некоторой области ограниченной полигоном

        Аргументы
        ---------
        `polygon`: Polygon или MultiPolygon
            Полигон или мультиполигон которым следует обрезать
            пространственные данные

        Возвращает
        ----------
        Данные того же типа обрезанные по полигону area
        '''


class RoadNetworkGraph(SpatialFeature):
    '''
    Граф дорожной сети.
    '''
    def __init__(self, spatial_data:nx.MultiDiGraph=None, name='RNG', path='rng.ml', **attr):
        super().__init__(spatial_data, name, path, **attr)

    def frame(self, polygon: Polygon, **attr):
        return ox.truncate.truncate_graph_polygon(self, polygon, **attr)

    def load(self, base_path='', **attr):
        '''Загрузка из файла-источника'''
        self._data = ox.load_graphml(f'{base_path}{self.path}', **attr)
        return self

    def save(self, base_path='', **attr):
        '''Сохранение в файл-источник'''
        ox.save_graphml(self.get, f'{base_path}{self.path}', **attr)
        return self

    def test(self):
        '''Проверить корректность данных'''
        print(str(self._data))
        return True

    def nodes(self, **attr):
        '''
        Узлы графа дорожной сети
        '''
        return self.get.nodes(**attr)


    @property
    def G(self):
        '''
        Исходный ГДС

        Возвращает
        ----------
        `nx.MultiDiGraph`
        '''
        return self.get

    @property
    def version(self):
        return '0.0.1'





class DataFeature(Feature):
    '''
    Класс непространственных данных
    '''

    def __init__(self, data:pd.DataFrame,
                 name='', path='', **attr):
        self._data = data
        super().__init__(name, path, **attr)



class SpeedProfile(DataFeature):
    '''
    Профиль скоростей
    '''
    def __init__(self, data: dict=None, name='SP', path='speeds.yml',
                speeds:list=[40,30,25,10,5], **attr):
        self._speeds_mm = {}
        self._name = name
        self._path = path
        if data is None:
            self._set_speeds(speeds)
        else:
            if not isinstance(data, dict):
                raise TypeError("Аргумент data должен быть только типа dict!")
            self._set_speeds_dict(data)


    def load(self, base_path='', **attr):
        '''Загрузка из файла-источника'''
        try:
            with open(f'{base_path}{self.path}', 'r', encoding='UTF-8') as file:
                data = yaml.load(file, Loader=yaml.FullLoader)
        except FileNotFoundError as exc:
            raise FileNotFoundError(f"Файл {base_path}{self.path} не существует!") from exc
        self._set_speeds_dict(data)
        return self

    def save(self, base_path='', **attr):
        '''Сохранение в файл-источник'''
        with open(f'{base_path}{self.path}', 'w', encoding='UTF-8') as outfile:
            yaml.dump(self.get, 
                      outfile,
                      sort_keys=False, 
                      default_flow_style=False)
        return self

    def test(self):
        '''Проверить корректность данных'''
        try:
            print(pd.DataFrame({'speeds':self.get}))
            super().test()
            return True
        except Exception as e:
            print(e)
            return False

    def __getitem__(self, item):
        '''Получение значения скорости по наименованию дороги из словаря'''
        speeds = self._speeds_mm
        if item in speeds.keys():
            return speeds[item]
        else:
            Warning(f"Объект {item} отсутствует в {self.name}!")
            return None

    def _set_speeds_dict(self, speeds:dict):
        '''
        Устанавливает скорости движения для всех типов улиц,
        переданных в соответствии с аргументом.

        Важно! Скорость указывается строго в км/ч

        Аргументы
        ---------

        `speeds`:dict
            Словарь скоростей движения по различным типам улиц.
            В словаре ключ - наименование типа улицы,
            значение - скорость движения по каждому из типов улиц
        
        Важно!
        ------
        Все типы дорог не указанные в `speeds` сохранят
        прежние значения (преднастроенные или 
        указанные при создании объекта)

        Пример
        ------
        ```
        sp = SP()
        sp.set_speeds_dict(
            {"motorway":40,
                "trunk":35
            }
        )
        ```
        '''
        if not isinstance(speeds, dict):
            raise TypeError("Аргумент speeds должен быть только типа dict!")

        speeds_mm = {}
        for k,v in speeds.items():
            speeds_mm[k]=kmh_to_mm(v)
        self._data = speeds
        self._speeds_mm = speeds_mm

    @property
    def _def_highways(self):
        '''Предопределенный список из 5 списков типов улиц.

        Не может быть переопределен прямым обращением:

        `sp._def_highways = list   #Так не работает!`

        0 - наиболее крупные автомагистрали
            ["motorway", "motorway_link", "trunk", "trunk_link", "primary", 
            "primary_link", "secondary", "secondary_link"]

        1 - остальные дороги: служебные проезды:, внутриквартальные,
        въездные, парковочные
            ["road", "unclassified", "tertiary", "tertiary_link"]
        
        2 - Жилые зоны и дворовые проезды
            ["living_street", "service", "residential", "track"]

        3 - Пешеходные дорожки, тротуары и прочие пригодные
        для движения автомобилей
            ["footway", "path", "pedestrian"]

        4 - области не являющиеся дорогами, но теоретически пригодные
        для перемещения пожарной техники
            ["steps", "cycleway", "bridleway", "corridor"]

        Более подробно о типах дорог можно прочесть здесь: 
        '''
        highways = [
            ["motorway", "motorway_link", "trunk", "trunk_link", "primary", 
            "primary_link", "secondary", "secondary_link"],

            ["road", "unclassified", "tertiary", "tertiary_link"],

            ["living_street", "service", "residential", "track"],

            ["footway", "path", "pedestrian"],

            ["steps", "cycleway", "bridleway", "corridor"]
        ]
        return highways

    def _set_speeds(self, speeds:list, def_highways:list[list]=None):
        '''Установка скоростей движения (км/ч)
        
        Аргументы
        ---------
        `speeds`:list
            Список скоростей в км/ч.
            Если указывается единственным аргументом,
            То должен состоять из 5 элементов (по количеству
            преднастроенных типов дорог -- см. `_def_highways`).
        `def_highways`:list[list]=None
            Список типов улиц для их переопределения.
            Заменяет значения
            Если указывается, то должен иметь длину равную длине
            `speeds`.

        Примеры
        -------
        Установка скоростей движения для 5 
        преднастроенных в SP групп дорог
        ```
        sp = SpeedProfile()
        sp._set_speeds(
            speeds = [60, 50, 35, 15, 2]
        )
        ```

        Установка скоростей для переопределенного списка из 6 групп дорог
        ```
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
        ```

        '''
        if def_highways is None:
            highway_types = self._def_highways
        else:
            if not len(speeds) == len(def_highways):
                raise ValueError("Количество элементов \
                                 в списках 'speeds' и \
                                 'def_highways' должно совпадать!")
            highway_types = def_highways
        highway_speeds = {}
        for speed, highway_list in zip(speeds, highway_types):
            for highway in highway_list:
                highway_speeds[highway]=speed
        self._set_speeds_dict(highway_speeds)

    @property
    def get(self):
        '''Словарь скоростей движения для разных типов дорог

        СТРОГО В КМ/Ч!
        
        Для получения значений в м/мин, следует воспользоваться
        ```
        SP['имя дороги']
        ```
        '''
        return dict(super().get)
    
    @property
    def version(self):
        return '0.0.1'




class Environment(Feature):        # Это уже реализация!!!
    '''
    Базовая реализация модели окружения. 
    В нее входит ГДС, размещение подразделений, объектов, и т.д.
    '''

    def __init__(self, name='E_Base', path='', **attr):
        super().__init__(name, path, **attr)

    def add_spatial_feature(self, spatial_feature: SpatialFeature):
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

        if not isinstance(spatial_feature, SpatialFeature):
            raise TypeError("аргумент 'spatial_feature' должен \
                            наследовать классу 'SpatialFeature'!")
        if spatial_feature.name=='':
            raise NameError("Для аргумента 'spatial_feature' \
                            не указано имя!")

        setattr(self, spatial_feature.name, spatial_feature)
        return self

    def add_data_feature(self, data: DataFeature, **attr):
        '''
        Добавление непространственных данных

        Аргументы
        ---------
        `data`: DataFeature
            Данные

        Возвращает
        ----------
        `self`: Environment
            Ссылка на самого себя
        '''

        if not isinstance(data, DataFeature):
            raise TypeError("Аргумент 'data' должен \
                            иметь тип данных 'DataFeature'!")
        if data.name=='':
            raise NameError("Для аргумента 'data' \
                            не указано имя!")
        setattr(self, data.name, data)
        return self
    
    def add_features(self, features_list:list):
        '''Добавление списка данных модели
        
        Аргументы
        ---------
        `features_list`:list
            Список моделей данных
        '''
        if not features_list:
            Warning("Список данных пуст!")
        for f in features_list:
            if isinstance(f, DataFeature):
                self.add_data_feature(f)
            if isinstance(f, SpatialFeature):
                self.add_spatial_feature(f)
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
        raise Warning("Данный метод еще на реализован, но он должен быть!")
        if feature_names is None:
            props_list = self.__dict__
        else:
            props_list = feature_names

        for prop_name in props_list:
            prop = getattr(self, prop_name)
            if isinstance(prop, SpatialFeature):
                prop.frame(polygon)
            

    def load(self, feature_names:list = None):
        '''Загрузка модели'''
        if feature_names is None:
            props_list = self.__dict__
        else:
            props_list = feature_names

        for prop_name in props_list:
            prop = getattr(self, prop_name)
            if isinstance(prop, Feature):
                prop.load(base_path=self.path)

    def save(self, feature_names:list = None):
        '''Сохранение модели'''
        if feature_names is None:
            props_list = self.__dict__
        else:
            props_list = feature_names

        for prop_name in props_list:
            prop = getattr(self, prop_name)
            if isinstance(prop, Feature):
                prop.save(base_path=self.path)

    def test(self):
        '''Проверить корректность данных'''
        test_result=1
        for item in self.__dict__.keys():
            prop = self.__dict__[item]
            if isinstance(prop, Feature):
                test_result*=prop.test()
        return bool(test_result)

    def __getitem__(self, item):
        if item in self.__dict__.keys():
            return self.__dict__[item]
        else:
            Warning(f"Объект {item} отсутствует в {self.name}!")
            return None

    @property
    def get(self):
        return self.__dict__



    # @property
    # def name(self):
    #     '''Имя набора данных'''
    #     return self._name
    # @name.setter
    # def name(self, name):
    #     self._name=name

    # @property
    # def path(self):
    #     '''Путь к файлу на диске'''
    #     return self._path
    # @path.setter
    # def path(self, path):
    #     self._path=path




# class Model(IModel):                    # Это уже реализация!!!
#     '''
#     Базовая реализация расчетной модели
#     '''


# class RoadNetworkGraph(nx.MultiDiGraph, IFeature, ISpatialFeature):
#     '''
#     Граф дорожной сети.
#     '''
#     def __init__(self, incoming_graph_data=None, multigraph_input=None, 
#                  name='RNG', path='data/rng.ml',
#                  **attr):
#         self.path=path
#         self.name=name
#         super().__init__(incoming_graph_data, multigraph_input, **attr)


#     def frame(self, polygon: Polygon, **attr):
#         return ox.truncate.truncate_graph_polygon(self, polygon, **attr)
    
#     def load(self):
#         '''Загрузка из файла-источника'''
#         # self = RoadNetworkGraph(ox.load_graphml(self.path))
#         return RoadNetworkGraph(ox.load_graphml(self.path))

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


