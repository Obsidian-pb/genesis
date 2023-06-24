'''
Реализация базовых моделей окружения (встроенные реализации)
'''

from .models import Environment
from .features import RoadNetworkGraph, DislocationProfile, SpeedProfile

class CommonEnvironment(Environment):
    '''Основная реализация модели окружения.
    Подходит для решения большинства самых распространенных задач

    Аргументы
    ---------
    `spatial_data`:Any=None
        Для моделей окружения не используется!
    `name`:str ='E_Base'
        Имя модели
    `path`:str =''
        Путь к папке модели. Настоятельно рекомендуется хранить 
        все файлы модели в одной папке

    Примеры
    -------
    Создание окружения из текущей папки
    ```
    E = CommonEnvironment().load() 
    E.crs = E.RNG.crs
    ```  

    Создание окружения из папки 'data/', расположенной в дочернем каталоге.
    ```
    E = CommonEnvironment(path='data/').load() 
    E.crs = E.RNG.crs
    ```   

    Создание окружения и загрузка ГДС с отличным от стандартного именем
    ```
    E = CommonEnvironment()
    E.RNG.path = 'test_rng.ml'      
    E.load()
    E.crs = E.RNG.crs
    ```
    '''

    _version='1'

    def __init__(self, spatial_data=None, name='E_Common', path='', **attr):
        # super().__init__(spatial_data, name, path, **attr)

        # Добавление дочерних моделей данных
        self.add_features(
            [
                RoadNetworkGraph(),
                DislocationProfile(),
                SpeedProfile()
            ]
        )

        super().__init__(spatial_data, name, path, **attr)