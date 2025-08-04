"""
Загрузка графа улично-дорожной сети из OSM при помощи osmnx

C:\Program Files\QGIS 3.34.11\apps\grass\grass84\scripts
"""

import networkx as nx
import osmnx as ox
import geopandas as gpd
from shapely.geometry import Polygon, box
from shapely.wkt import loads

# print(ox.__version__)
# print(nx.__version__)
# print(gpd.__version__)


from qgis.PyQt.QtCore import QCoreApplication, QVariant
from qgis.core import (QgsProcessing,
                       QgsWkbTypes,
                       QgsField,
                       QgsFields,
                       QgsFeatureSink,
                       QgsFeature,
                       QgsGeometry,
                       QgsPointXY,
                       QgsProcessingException,
                       QgsProcessingAlgorithm,
                       QgsProcessingParameterFeatureSource,
                       QgsProcessingParameterExtent,
                       QgsProcessingParameterFeatureSink)
from qgis import processing
# from qgis import WkbType


class GDownloadAlgorithm(QgsProcessingAlgorithm):
    """
    Алгоритм загрузки графа улично-дорожной сети из OSM при помощи osmnx
    """

    INPUT = 'INPUT'
    OUTPUT = 'OUTPUT'

    def tr(self, string):
        """
        Returns a translatable string with the self.tr() function.
        """
        return QCoreApplication.translate('Processing', string)

    def createInstance(self):
        return GDownloadAlgorithm()

    def name(self):
        """
        Название алгоритма
        """
        return 'g_download_by_osmnx'

    def displayName(self):
        """
        Отображаемое в списке имя алгоритма
        """
        return self.tr('Загрузка графа УДС из OSMNX')

    def group(self):
        """
        Отображаемое в списке имя группы
        """
        return self.tr('Графы')

    def groupId(self):
        """
        ID группы алгоритмов
        """
        return 'graphs'

    def shortHelpString(self):
        """
        Строка подсказки
        """
        return self.tr("Загрузка графа улично-дорожной сети из OSM при помощи osmnx")

    def initAlgorithm(self, config=None):
        """
        Здесь указываются настройки алгоритма - входы и выходы.
        Все это будет указываться в окне интерфейса алгоритма.
        """

        # Охват карты
        self.addParameter(
            QgsProcessingParameterExtent  (
                self.INPUT,
                self.tr('Охват карты')
            )
        )


        # Выходной слой 
        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.OUTPUT,
                self.tr('Выходной слой')
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        """
        Here is where the processing itself takes place.
        """

        # Retrieve the feature source and sink. The 'dest_id' variable is used
        # to uniquely identify the feature sink, and must be included in the
        # dictionary returned by the processAlgorithm function.
        extent = self.parameterAsExtent(
            parameters,
            self.INPUT,
            context
        )

        # Получем исходную crs:
        crs = self.parameterAsGeometryCrs(
            parameters,
            self.INPUT,
            context
        )
        feedback.pushInfo(crs.authid())

        # Формируем полигон для выгрузки графа дорог
        xmin = extent.xMinimum()
        ymin = extent.yMinimum()
        xmax = extent.xMaximum()
        ymax = extent.yMaximum()
        poly = Polygon().from_bounds(xmin, ymin, xmax, ymax)

        # Загрузка данных из osmnx
        G = ox.graph_from_polygon(poly, network_type='drive_service', simplify=False)

        # Вывод отчета о количестве полученных узлов
        feedback.pushInfo('Получен граф дорог с количеством узлов:')
        feedback.pushInfo(str(G.number_of_nodes()))

        # If source was not found, throw an exception to indicate that the algorithm
        # encountered a fatal error. The exception text can be any string, but in this
        # case we use the pre-built invalidSourceError method to return a standard
        # helper text for when a source cannot be evaluated
        if extent is None:
            raise QgsProcessingException(self.invalidSourceError(parameters, self.INPUT))

        # Подготвливаем перечень полей
        fields = QgsFields()
        fields.append(QgsField(name = 'osmid',
                    type = QVariant.Int,
                    typeName = 'Integer64')
            )
        fields.append(QgsField(name = 'lanes',
                    type = QVariant.String,
                    typeName = 'String')
            )
        fields.append(QgsField(name = 'highway',
                    type = QVariant.String,
                    typeName = 'String')
            )
        fields.append(QgsField(name = 'oneway',
                    type = QVariant.Int,
                    typeName = 'Boolean')
            )
        fields.append(QgsField(name = 'reversed',
                    type = QVariant.String,
                    typeName = 'Boolean')
            )
        fields.append(QgsField(name = 'length',
                    type = QVariant.Double,
                    typeName = 'Real')
            )
        fields.append(QgsField(name = 'name',
                    type = QVariant.String,
                    typeName = 'String')
            )
        fields.append(QgsField(name = 'maxspeed',
                    type = QVariant.String,
                    typeName = 'String')
            )
        fields.append(QgsField(name = 'bridge',
                    type = QVariant.String,
                    typeName = 'String')
            )
        fields.append(QgsField(name = 'junction',
                    type = QVariant.String,
                    typeName = 'String')
            )
        fields.append(QgsField(name = 'service',
                    type = QVariant.String,
                    typeName = 'String')
            )
        fields.append(QgsField(name = 'tunnel',
                    type = QVariant.String,
                    typeName = 'String')
            )
        fields.append(QgsField(name = 'access',
                    type = QVariant.String,
                    typeName = 'String')
            )

        # Формируем выходной слой
        (sink, dest_id) = self.parameterAsSink(
            parameters,
            self.OUTPUT,
            context,
            fields,
            QgsWkbTypes.LineString,
            crs,
        )



        # Формируем фичи - не забыть про геометрию!!!
        edges = ox.graph_to_gdfs(G, nodes = False)
        total = 100 / len(edges)
        i=0
        for _, data in edges.iterrows():
            i += 1
            geom = QgsGeometry.fromWkt(str(data['geometry']))
            feat = QgsFeature(fields)
            feat.setGeometry(geom)
            feat.setAttribute('osmid', data['osmid'])
            feat.setAttribute('lanes', data['lanes'])
            feat.setAttribute('highway', data['highway'])
            feat.setAttribute('reversed', data['reversed'])
            feat.setAttribute('length', data['length'])
            if data['name']: feat.setAttribute('name', data['name'])
            feat.setAttribute('maxspeed', data['maxspeed'])
            feat.setAttribute('bridge', data['bridge'])
            # feat.setAttribute('junction', data['junction'])
            feat.setAttribute('service', data['service'])
            feat.setAttribute('tunnel', data['tunnel'])
            # feat.setAttribute('access', data['access'])
            sink.addFeature(feat, QgsFeatureSink.FastInsert)

            # Обновление прогрессбара
            feedback.setProgress( int(i * total) )
        





        # Что-то выводим в окно алгоритма
        # feedback.pushInfo(f'CRS is {source.sourceCrs().authid()}')

        # If sink was not created, throw an exception to indicate that the algorithm
        # encountered a fatal error. The exception text can be any string, but in this
        # case we use the pre-built invalidSinkError method to return a standard
        # helper text for when a sink cannot be evaluated
        if sink is None:
            raise QgsProcessingException(self.invalidSinkError(parameters, self.OUTPUT))


        return {self.OUTPUT: dest_id}
