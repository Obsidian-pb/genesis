'''
Реализация базовых моделей окружения (встроенные реализации)
'''

from .models import Environment
from .features import RoadNetworkGraph, DislocationProfile, SpeedProfile

class CommonEnvironment(Environment):

    def __init__(self, spatial_data=None, name='E_City', path='', **attr):
        super().__init__(spatial_data, name, path, **attr)

        # Добавление дочерних моделей данных
        self.add_features(
            [
                RoadNetworkGraph(path='rng.ml'),
                DislocationProfile(),
                SpeedProfile()
            ]
        )

        super().__init__(spatial_data, name, path, **attr)