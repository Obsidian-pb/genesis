'''
Базовые модели данных
'''

from abc import abstractmethod
# from typing import Any
import logging as lg

import pandas as pd
# import geopandas as gpd
# import networkx as nx
# import osmnx as ox
# import yaml
from shapely.geometry import MultiPolygon, Polygon

# from genesis.tools import kmh_to_mm
# from genesis.interfaces import IFeature, IEnvironment, ISpatialFeature, IModel, IDataFeature
# from genesis.tools import kmh_to_mm

# === Базовые модели ===

class Feature(object):
    '''
    Базовый класс модели данных
    '''
    _path=''
    _name=''
    _data=None
    _version='0'

    def __init__(self,
                 name='', path='',
                 **attr):
        self.path=path
        self._name=name

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
    # @name.setter
    # def name(self, name):
    #     self._name=name

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
        if self._data is None:
            raise ValueError("Носимые данные модели не установлены. Необходимо либо передать их при создании экземпляра класса, либо загрузить при помощи метода .load()")
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
        Рекомендуется указывать в формате номер строкой `*`,
        например, '17'.
        Рекомендуется указывать только для рабочих
        реализаций классов - например, для `RoadNetworkGraph`,
        но не для `SpatialFeature`'''
        return self._version


class SpatialFeature(Feature):
    '''
    Базовый класс модели пространственных данных
    '''
    _crs=None     # СК меодели

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

class DataFeature(Feature):
    '''
    Базовый класс непространственных данных
    '''

    def __init__(self, data:pd.DataFrame,
                 name='', path='', **attr):
        self._data = data
        super().__init__(name, path, **attr)


class Environment(SpatialFeature):
    '''
    Базовый класс модели окружения. 
    
    Аргументы
    ---------
    `spatial_data`:Any=None
        Для моделей окружения не используется!
    `name`:str ='E_Base'
        Имя модели
    `path`:str =''
        Путь к папке модели. Настоятельно рекомендуется хранить 
        все файлы модели в одной папке
    '''

    def __init__(self, spatial_data=None, name='E_Base', path='', **attr):
        if not spatial_data is None:
            if isinstance(spatial_data, list):
                self.add_features(spatial_data)
            else:
                self.add_features([spatial_data])
        super().__init__(spatial_data=None, name=name, path=path, **attr)

    def add_spatial_feature(self, spatial_feature: SpatialFeature):
        '''
        Добавление пространственных данных
        
        Аргументы
        ---------
        `spatial_feature`: SpatialFeature
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
                self[key].crs = crs



class Computer(object):
    '''Базовый класс вычислительной модели.
    Расчетная модель описывает всю логику вычислений

    Аргументы
    ---------
    `E`:Environment
        Модель окружения
    '''

    # Версия вычислительной модели
    _version='0'

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

    @property
    def version(self):
        '''Версия реализации модели.
        Рекомендуется указывать в формате номер строкой `*`,
        например, '17'.
        Рекомендуется указывать только для рабочих
        реализаций классов - например, для `RoadNetworkGraph`,
        но не для `SpatialFeature`'''
        return self._version