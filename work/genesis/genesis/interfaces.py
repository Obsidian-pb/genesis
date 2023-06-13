'''
Интерфейсы
'''

# from abc import ABCMeta, abstractmethod, abstractproperty

import networkx as nx
from shapely.geometry import Polygon, MultiPolygon




class ISpatialFeature():
    '''
    Интерфейс пространственных данных
    '''

    def frame(self, polygon: Polygon or MultiPolygon, **attr):
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


class IEnvironment():
    '''
    Интерфейс модели окружения
    '''
    # __metaclass__=ABCMeta


    # @abstractmethod
    def add_spatial_feature(self, spatial_feature: ISpatialFeature, **attr):
        '''Добавить пространственные данные'''

    def add_data(self, data):
        '''Добавление непространственных данных'''

    def frame(self, polygon: Polygon or MultiPolygon, **attr):
        '''Получение фрагмента Окружения'''

    def load(self, **attr):
        '''Загрузка модели'''

    def save(self, **attr):
        '''Сохранение модели'''

    # @abstractmethod
    def test(self):
        '''Проверить корректность модели'''



class IModel():
    '''
    Интерфейс расчетной модели
    '''
    ssfpl = nx.single_source_dijkstra_path_length
    msfpl = nx.multi_source_dijkstra_path_length


    delay_time = 1

    # @abstractmethod
    def execute(self):
        '''
        Запуск вычислений
        '''

