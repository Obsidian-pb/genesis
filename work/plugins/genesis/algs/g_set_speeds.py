"""
Загрузка графа улично-дорожной сети из OSM при помощи osmnx.

Сохранение напрямую в файл geopackage и загрузка слоя в проект.
"""

import networkx as nx
import osmnx as ox
import geopandas as gpd
from shapely.geometry import Polygon, box
from shapely.wkt import loads


from qgis.PyQt.QtCore import QCoreApplication
from qgis.core import (
                       QgsProject,
                       QgsVectorLayer,
                       QgsProcessingException,
                       QgsProcessingAlgorithm,
                       QgsProcessing,
                       QgsProcessingParameterFileDestination,
                       QgsProcessingParameterExtent,
                       QgsProcessingParameterString,
                       QgsProcessingParameterFeatureSource,
                       QgsProcessingParameterBoolean,
                       QgsCoordinateReferenceSystem,
                       QgsCoordinateTransform,
                       )
# from qgis import processing

# from .graph_tools import fix_highway_list



class GDSSpeedsAlgorithm(QgsProcessingAlgorithm):
    """
    Алгоритм загрузки графа улично-дорожной сети из OSM при помощи osmnx

    Сохранение напрямую в файл geopackage и загрузка слоя в проект.
    """

    INPUT = 'INPUT'
    OUTPUT = 'OUTPUT'

    def tr(self, string):
        """
        Возвращает перевод для self.tr().
        """
        return QCoreApplication.translate('Processing', string)

    def createInstance(self):
        return GDSSpeedsAlgorithm()

    def name(self):
        """
        Название алгоритма
        """
        return 'g_download_by_osmnx'

    def displayName(self):
        """
        Отображаемое в списке имя алгоритма
        """
        return self.tr('Загрузка ГДС из OSMNX по охвату')

    def group(self):
        """
        Отображаемое в списке имя группы
        """
        return self.tr('ГДС')

    def groupId(self):
        """
        ID группы алгоритмов
        """
        return 'rng'

    def shortHelpString(self):
        """
        Строка подсказки
        """
        return self.tr(
            '''Загрузка графа улично-дорожной сети из OSM при помощи osmnx.
            Сохранение напрямую в файл geopackage и загрузка слоя в проект.'''
            )

    def initAlgorithm(self, config=None):
        """
        Здесь указываются настройки алгоритма - входы и выходы.
        Все это будет указываться в окне интерфейса алгоритма.
        """

        # Слой дорожной сети
        self.addParameter(
            QgsProcessingParameterFeatureSource (
                self.INPUT,
                self.tr('Слой границ'),
                [QgsProcessing.TypeVectorPolygon]
            )
        )

        # Расчетные скорости следования
        self.addParameter(
            QgsProcessingParameterBoolean (
                'SPEEDS',
                self.tr('Упростить граф'),
                False
            )
        )

        

    def processAlgorithm(self, parameters, context, feedback):
        """
        Код алгоритма
        """
        feedback.pushInfo('Версии библиотек:')
        feedback.pushInfo(f'   osmnx: {ox.__version__}')
        feedback.pushInfo(f'   networkx: {nx.__version__}')
        feedback.pushInfo(f'   geopandas: {gpd.__version__}')

        # Получение исходных параметров алгоритма
        ## Загрузка охвата
        layer = self.parameterAsVectorLayer(
            parameters,
            self.INPUT,
            context
        )
        ### Проверяем корректность охвата
        if layer is None:
            raise QgsProcessingException(self.invalidSourceError(parameters, self.INPUT))

        


        # Тело алгоритма
        # Активируем возможность редактирования слоя

        # Перебираем все фичи слоя:

        ## Устанавливаем для каждой фичи скорость и время следования

        # Сохраняем изменения в слое и закрываем редактирование


        


        # dest_id = '0'
        return {self.OUTPUT: 'Ok'}

