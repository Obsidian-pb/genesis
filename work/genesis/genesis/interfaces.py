'''
Интерфейсы
'''

from abc import ABCMeta, abstractmethod, abstractproperty

import networkx as nx
import pandas as pd
from shapely.geometry import Polygon, MultiPolygon


class IFeature():
    '''
    Базовый интерфейс данных модели
    '''
    __metaclass__=ABCMeta

    def __init__(self, name:str, path:str) -> None:
        pass

    @abstractmethod
    def load(self):
        '''Загрузка из файла-источника'''

    @abstractmethod
    def save(self):
        '''Сохранение в файл-источник'''

    @abstractmethod
    def test(self):
        '''Проверить корректность данных'''

    @property
    @abstractmethod
    def name(self):
        '''Имя набора данных'''

    @property
    @abstractmethod
    def path(self):
        '''Основной путь к файлу-источнику'''




class ISpatialFeature():
    '''
    Интерфейс пространственных данных
    '''
    __metaclass__=ABCMeta

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

class IDataFeature():
    '''
    Интерфейс данных не имеющих пространственной привязки
    '''
    __metaclass__=ABCMeta







class IEnvironment():
    '''
    Интерфейс модели окружения
    '''
    __metaclass__=ABCMeta

    # МЕТОДЫ:
    @abstractmethod
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
        '''

    @abstractmethod
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

    # СВОЙСТВА: 
    # Возможно лучше определять по ходу работы
    # @abstractproperty
    # def speed():





class IModel():
    '''
    Интерфейс расчетной модели
    '''
    __metaclass__=ABCMeta

    # В свойства!!!:
    # ssfpl = nx.single_source_dijkstra_path_length
    # msfpl = nx.multi_source_dijkstra_path_length
    # delay_time = 1

    @abstractmethod
    def execute(self):
        '''
        Запуск вычислений
        '''


