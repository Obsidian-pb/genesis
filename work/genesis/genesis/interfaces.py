'''
Интерфейсы
'''

import networkx as nx

from abc import ABCMeta, abstractmethod, abstractproperty

class IEnvironment():
    '''
    Интерфейс модели окружения
    '''
    __metaclass__=ABCMeta

    # @abstractproperty
    # def 

    @abstractmethod
    def add_spatial_feature(self, spatial_feature):
        '''Добавить пространственные данные'''


    @abstractmethod
    def test(self):
        '''Проверить корректность модели'''



class IModel():
    '''
    Интерфейс расчетной модели
    '''
    ssfpl = nx.single_source_dijkstra_path_length
    msfpl = nx.multi_source_dijkstra_path_length


    delay_time = 1

    @abstractmethod
    def execute(self):
        '''
        Запуск вычислений
        '''