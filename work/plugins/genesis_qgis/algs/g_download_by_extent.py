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
                       QgsProcessingParameterFileDestination,
                       QgsProcessingParameterExtent,
                       QgsProcessingParameterString,
                       QgsProcessingParameterBoolean,
                       QgsCoordinateReferenceSystem,
                       QgsCoordinateTransform,
                       )
from qgis import processing

from graphs.algorithms import fix_highway_list



class GDownloadAlgorithm(QgsProcessingAlgorithm):
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
        return self.tr('Загрузка ГДС из OSMNX по охвату')

    def group(self):
        """
        Отображаемое в списке имя группы
        """
        return self.tr('Графы улично-дорожной сети')

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

        # Охват карты
        self.addParameter(
            QgsProcessingParameterExtent (
                self.INPUT,
                self.tr('Охват карты')
            )
        )

        # Необходимо ли произвести упрощение графа
        # self.addParameter(
        #     QgsProcessingParameterBoolean (
        #         'SIMPLIFY',
        #         self.tr('Упростить граф'),
        #         False
        #     )
        # )

        # Необходимо ли получить все компоненты графа
        self.addParameter(
            QgsProcessingParameterBoolean (
                'RETAIN',
                self.tr('Получить несвязанные компоненты'),
                False
            )
        )

        # Имя слоя дорожной сети
        self.addParameter(
            QgsProcessingParameterString (
                'RNG',
                self.tr('Имя слоя дорожной сети'),
                'Дорожная сеть'
            )
        )


        # Выходной слой
        self.addParameter(
            QgsProcessingParameterFileDestination(
                self.OUTPUT,
                self.tr('Выходной файл'),
                'файл Geopackage (*.gpkg)',
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
        extent = self.parameterAsExtent(
            parameters,
            self.INPUT,
            context
        )
        ### Проверяем корректность охвата
        if extent is None:
            raise QgsProcessingException(self.invalidSourceError(parameters, self.INPUT))

        ## Получем исходную crs:
        crs = self.parameterAsExtentCrs (
            parameters,
            self.INPUT,
            context
        )
        ### Проверяем корректность CRS
        if crs is None:
            raise QgsProcessingException(self.invalidSourceError(parameters, self.INPUT))
        feedback.pushInfo(crs.authid())

        # ## Получаем флаг необходимости упрощения графа
        # simplify = self.parameterAsBoolean(
        #     parameters,
        #     'SIMPLIFY',
        #     context
        # )
        # if simplify is None:
        #     raise QgsProcessingException(self.invalidSourceError(parameters, self.INPUT))
        
        ## Получаем флаг необходимости получения изолированных компонентов
        retain_all = self.parameterAsBoolean(
            parameters,
            'RETAIN',
            context
        )
        if retain_all is None:
            raise QgsProcessingException(self.invalidSourceError(parameters, self.INPUT))

        ## Получаем имя слоя дорожной сети
        layer_name = self.parameterAsString(
            parameters,
            'RNG',
            context
        )
        if layer_name == '':
            raise QgsProcessingException(self.invalidSourceError(parameters, self.INPUT))

        ## Получаем путь по которому следует сохранить граф
        target_file = self.parameterAsFile(
            parameters,
            self.OUTPUT,
            context
        )
        ### Если target_file не был получен
        if target_file is None:
            raise QgsProcessingException(self.invalidSinkError(parameters, self.OUTPUT))


        # Тело алгоритма
        # Если необходимо производим перепроецирование СК полигона
        if crs.authid() != 'EPSG:4326':
            feedback.pushInfo(f'Текущая СК ({crs.authid()}) для охвата будет приведена к СК WGS 84 [EPSG: 4326]')
            crs_source = crs
            crs_dest = QgsCoordinateReferenceSystem("EPSG:4326")
            transformContext = QgsProject.instance().transformContext()
            xform = QgsCoordinateTransform(crs_source, crs_dest, transformContext)
            extent  = xform.transform(extent)

        # Формируем полигон для выгрузки графа дорог
        xmin = extent.xMinimum()
        ymin = extent.yMinimum()
        xmax = extent.xMaximum()
        ymax = extent.yMaximum()
        poly = Polygon().from_bounds(xmin, ymin, xmax, ymax)


        # Загрузка данных из osmnx
        G = ox.graph_from_polygon(poly, network_type='drive_service',
                                  simplify=False,
                                  retain_all=retain_all)
        ## Если был передан флаг упрощения графа - упрощаем его
        # if simplify:
        #     G = ox.simplify_graph(G, edge_attrs_differ=['highway', 'oneway', 'reversed'])
        ## Вывод отчета о количестве полученных узлов
        feedback.pushInfo(f'Получен граф дорог с количеством узлов - {G.number_of_nodes()} и ребер {G.number_of_edges()}')




        # Сохраняем граф как файл Geopackage
        edges = ox.graph_to_gdfs(G, nodes=False)
        ## Если граф был упрощен, исправляем типы улиц list
        # if simplify:
        #     for column in edges.columns:
        #         edges[column] = edges[column].apply(fix_highway_list)
        # Сохранение
        edges.to_file(target_file)
        feedback.pushInfo(f'Граф сохранен как {str(target_file)}')

        # Добавляем полученный слой на карту
        vlayer = QgsVectorLayer(target_file, layer_name, 'ogr')
        QgsProject.instance().addMapLayer(vlayer)


        return {self.OUTPUT: target_file}

