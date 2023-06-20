'''
Модели используемые в расчетах
'''

from abc import abstractmethod
# from typing import Any
import logging as lg

import pandas as pd
import geopandas as gpd
import networkx as nx
import osmnx as ox
import yaml
from shapely.geometry import MultiPolygon, Polygon

# from genesis.tools import kmh_to_mm
# from genesis.interfaces import IFeature, IEnvironment, ISpatialFeature, IModel, IDataFeature
from genesis.tools import kmh_to_mm

class Feature(object):
    '''
    Базовый класс модели данных
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
    def data(self):
        '''Носимые данные модели'''
        return self._data
    @data.setter
    def data(self, data):
        '''Носимые данные модели'''
        self._data=data

    @property
    def get(self):
        '''Носимые данные модели'''
        lg.warning("Метод .get устарел и будет удален в следующих версиях. Вместо него используйте свойство .data")
        return self._data
    
    @property
    def version(self):
        '''Версия реализации модели.
        Рекомендуется указывать в формате `*.*.*`
        Рекомендуется указывать только для рабочих
        реализаций классов - например, для `RoadNetworkGraph`,
        но не для `SpatialFeature`'''
        return '0.0.0'


class SpatialFeature(Feature):
    '''
    Базовый класс модели пространственных данных
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

    @property
    @abstractmethod
    def crs(self):
        '''СК носимых данных объекта
        '''
    @crs.setter
    def crs(self, crs):
        pass


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
        ox.save_graphml(self.data, f'{base_path}{self.path}', **attr)
        return self

    def test(self):
        '''Проверить корректность данных'''
        print(str(self._data))
        return True

    def nodes(self, **attr):
        '''
        Узлы графа дорожной сети
        '''
        return self.data.nodes(**attr)

    @property
    def crs(self):
        return self.data.graph['crs']
    @crs.setter
    def crs(self, crs):
        self.data = ox.project_graph(self.data, crs)

    @property
    def G(self):
        '''
        Исходный ГДС из носимых данных

        Возвращает
        ----------
        `nx.MultiDiGraph`
        '''
        return self.data

    @property
    def version(self):
        return '0.0.3'





class DataFeature(Feature):
    '''
    Базовый класс непространственных данных
    '''

    def __init__(self, data:pd.DataFrame,
                 name='', path='', **attr):
        self._data = data
        super().__init__(name, path, **attr)



class SpeedProfile(DataFeature):
    '''
    Класс профиля скоростей
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
        return dict(self.data)
    
    @property
    def version(self):
        return '0.0.1'



class DislocationProfile(SpatialFeature):
    '''
    Класс профиля дислокации
    '''

    def __init__(self, spatial_data: gpd.GeoDataFrame=None,
                 name='DP',
                 path='stations.gpkg',
                 layer_name='Подразделения',
                 **attr):
        self.layer_name = layer_name
        super().__init__(spatial_data, name, path, **attr)

    def load(self, base_path='', layer_name:str=None, **attr):
        '''Загрузка из файла-источника'''
        if layer_name is None:
            layer_name = self.layer_name

        try:
            data = gpd.read_file(f'{base_path}{self.path}', **attr)
        except FileNotFoundError as exc:
            raise FileNotFoundError(f"Файл {base_path}{self.path} не существует!") from exc
        data = data.set_index('name')
        self._data = data
        return self

    def save(self, base_path='', **attr):
        '''Сохранение в файл-источник'''
        if layer_name is None:
            layer_name = self.layer_name

        self.get.to_file(f'{base_path}{self.path}', 
                     driver="GPKG", 
                     layer=layer_name, index=True)
        return self

    def frame(self, polygon: Polygon | MultiPolygon, **attr):
        '''Реализовать!
        '''
        lg.debug("Метод frame класса DislocationProfile не реализован!")
        return super().frame(polygon, **attr)
    

    def __getitem__(self, item:str):
        '''Получение записи об одном из подразделений по его имени'''
        if item in self.get.index:
            return self.get.loc[item]
        else:
            lg.debug(f"Подразделение {item} отсутствует в профиле дислокации!")
            return None

    @property
    def get(self):
        '''GeoDataFrame территориальных подразделений
        '''
        return gpd.GeoDataFrame(super().get)
    
    @property
    def crs(self):
        return self.data.crs
    @crs.setter
    def crs(self, crs):
        self.data = self.data.to_crs(crs)

    @property
    def version(self):
        return '0.0.1'

    def test(self):
        '''Проверить корректность данных'''
        if self._data is None:
            print("Данные модели не установлены")
            return False

        if not self.get.index.name == 'name':
            print("Индекс данных не установлен или имеет имя отличное от 'name")
            return False

        columns = [
            'description', 'type', 'class'
        ]
        if not all([col in self.get.columns for col in columns]):
            print('Не все требуемые поля имеются в наборе данных!')
            return False
        self.get.head()
        return True




class Environment(SpatialFeature):
    '''
    Базовый класс модели окружения. 
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
            lg.warning("Список данных пуст!")
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
            

    def load(self, base_path=None, feature_names:list = None):
        '''Загрузка модели'''
        if feature_names is None:
            props_list = self.__dict__
        else:
            props_list = feature_names

        for prop_name in props_list:
            prop = getattr(self, prop_name)
            if isinstance(prop, Feature):
                if base_path is None:
                    prop.load(base_path=self.path)
                else:
                    prop.load(base_path)
        return self

    def save(self, base_path=None, feature_names:list = None):
        '''Сохранение модели'''
        if feature_names is None:
            props_list = self.__dict__
        else:
            props_list = feature_names

        for prop_name in props_list:
            prop = getattr(self, prop_name)
            if isinstance(prop, Feature):
                if base_path is None:
                    prop.save(base_path=self.path)
                else:
                    prop.save(base_path)
        return self

    def test(self):
        '''Проверить корректность данных'''
        test_result=1
        for key, prop in self.__dict__.items():
            # prop = self.__dict__[item]
            if isinstance(prop, Feature):
                test_result*=prop.test()
        return bool(test_result)

    def __getitem__(self, item):
        if item in self.__dict__.keys():
            return self.__dict__[item]
        else:
            lg.warning(f"Объект {item} отсутствует в {self.name}!")
            return None

    @property
    def crs(self):
        return self._crs
    @crs.setter
    def crs(self, crs):
        self._crs = crs
        for key, prop in self.__dict__.items():
            if isinstance(prop, SpatialFeature):
                self[key].data.crs = crs









class Computer(object):

    # Настройки модели компьютера
    # ssfpl = nx.single_source_dijkstra_path_length
    # msfpl = nx.multi_source_dijkstra_path_length
    # delay_time = 1

    def __init__(self, E:Environment, **kwargs):
        self.environment = E

    def set_settings(self, **kwargs):
        '''Установка настроек модели компьютера
        '''
        for k,v in kwargs.items():
            setattr(self, k, v)
        return self

    @property
    def environment(self):
        return self.E

    @environment.setter
    def environment(self, E:Environment):
        self.E = E
        return self
    
    @abstractmethod
    def execute(self):
        # Здесь описывается последовательность выполняемых действий
        return self