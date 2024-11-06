"""
Расчет кратчайшего маршрута между двумя точками
"""

import os


import networkx as nx
import osmnx as ox
import geopandas as gpd

from ..graphs.speeds import kmh_to_mm, set_graph_travel_times
# from shapely.geometry import Polygon, box
# from shapely.wkt import loads


from ..graphs.algorithms import graph_rise_from_gpkg
from qgis.PyQt.QtCore import QCoreApplication, QVariant
from qgis.PyQt.QtGui import QIcon

from qgis.core import (
                       QgsProject,
                       QgsVectorLayer,
                       QgsField,
                       QgsProcessingException,
                       QgsProcessingAlgorithm,
                       QgsProcessing,
                       QgsProcessingParameterFileDestination,
                    #    QgsProcessingParameterExtent,
                       QgsProcessingParameterString,
                       QgsProcessingParameterPoint,
                       QgsProcessingParameterField,
                       QgsProcessingParameterFeatureSource,
                       QgsProcessingParameterBoolean,
                       QgsProcessingParameterDefinition,
                       QgsCoordinateReferenceSystem,
                       QgsCoordinateTransform,
                       )



pluginPath = os.path.split(os.path.split(os.path.dirname(__file__))[0])[0]



class ShortestPathP2PAlgorithm(QgsProcessingAlgorithm):
    """
    Расчет кратчайшего маршрута между двумя точками.
    """

    INPUT = 'INPUT'
    START_POINT = 'START_POINT'
    END_POINT = 'END_POINT'
    TRAVEL_TIME_FIELD = 'TRAVEL_TIME_FIELD'
    RESULT_FIELD = 'RESULT_FIELD'
    SIMPLIFY = 'SIMPLIFY'
    OUTPUT = 'OUTPUT'

    def icon(self):
        return QIcon(os.path.join(pluginPath, 'QNEAT3', 'icons', 'icon_dijkstra_onetoone.svg'))


    def tr(self, string):
        """
        Возвращает перевод для self.tr().
        """
        return QCoreApplication.translate('Processing', string)

    def createInstance(self):
        return ShortestPathP2PAlgorithm()

    def name(self):
        """
        Название алгоритма
        """
        return 'a_shortest_path_p2p'

    def displayName(self):
        """
        Отображаемое в списке имя алгоритма
        """
        return self.tr('Расчет маршрута между 2 точками')

    def group(self):
        """
        Отображаемое в списке имя группы
        """
        return self.tr('Прибытие')

    def groupId(self):
        """
        ID группы алгоритмов
        """
        return 'ArrivalParams'

    def shortHelpString(self):
        """
        Строка подсказки
        """
        return self.tr(
            '''
            Расчет кратчайшего маршрута между двумя точками.
            '''
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
                self.tr('Слой улично-дорожной сети'),
                [QgsProcessing.TypeVectorLine]
            )
        )

        # Точки старта и финиша
        self.addParameter(QgsProcessingParameterPoint(self.START_POINT,
                                                      self.tr('Стартовая точка')))
        self.addParameter(QgsProcessingParameterPoint(self.END_POINT,
                                                      self.tr('Конечная точка')))
        # Работаем с упрощенным графом или нет
        self.addParameter(QgsProcessingParameterBoolean(self.SIMPLIFY, self.tr('Упростить граф'), True))

        # Поле названия итогового слоя
        self.addParameter(
            QgsProcessingParameterString (
                self.RESULT_FIELD,
                self.tr('Имя итогового слоя'),
                'Маршрут'
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
        travel_time_field = 'travel_time'


        feedback.pushInfo('Версии библиотек:')
        feedback.pushInfo(f'   osmnx: {ox.__version__}')
        feedback.pushInfo(f'   networkx: {nx.__version__}')
        feedback.pushInfo(f'   geopandas: {gpd.__version__}')

        # Получение исходных параметров алгоритма
        ## Загрузка охвата
        network = self.parameterAsSource(parameters, self.INPUT, context)
        ### Проверяем корректность охвата
        if network is None:
            raise QgsProcessingException(self.invalidSourceError(parameters, self.INPUT))

        ## Получение СК
        crs = self.parameterAsExtentCrs(parameters, self.INPUT, context)

        start_point = self.parameterAsPoint(parameters, self.START_POINT, context, network.sourceCrs()) #QgsPointXY
        end_point = self.parameterAsPoint(parameters, self.END_POINT, context, network.sourceCrs()) #QgsPointXY
        # travel_time_field = self.parameterAsString(parameters, self.TRAVEL_TIME_FIELD, context) #str
        target_file = self.parameterAsFile(parameters, self.OUTPUT, context)
        layer_name = self.parameterAsString(parameters, self.RESULT_FIELD, context)
        simplify = self.parameterAsBoolean(parameters, self.SIMPLIFY, context)


        # Тело алгоритма
        feedback.setProgress(0)
        # Подготавливаем геодатасет с геометрией дорог
        roads = gpd.GeoDataFrame.from_features(list(network.getFeatures()), crs=crs.authid())
        try:
            roads = ox.project_gdf(roads)
        except:
            feedback.pushInfo('Перепроецирование слоя улично-дорожной сети не требуется')
        feedback.setProgress(30)

        # Формируем граф
        G = graph_rise_from_gpkg(roads,
                                 columns_list = ['name', 'highway', 'oneway', 'lanes', 'reversed'])
        if simplify:
            G = ox.simplify_graph(G)
        g_crs = G.graph['crs']
        feedback.pushInfo(f'Получен граф дорог с количеством узлов - {G.number_of_nodes()} и ребер {G.number_of_edges()}. СК: {g_crs}')
        feedback.setProgress(70)

        # Устанавливаем скорости следования
        speeds = [50, 40, 30, 15, 5]
        set_graph_travel_times(G, speeds, morph_function=kmh_to_mm, travel_time_field=travel_time_field)
        feedback.setProgress(80)

        # Перепроецируем точки начала и конца маршрута в СК полученного графа
        if crs.authid() != g_crs:
            feedback.pushInfo(f'Текущая СК ({crs.authid()}) для охвата будет приведена к локальной метрической СК {g_crs}')
            crs_source = crs
            crs_dest = QgsCoordinateReferenceSystem(str(g_crs))
            transformContext = QgsProject.instance().transformContext()  # Возможно здеь нужен слой
            tf = QgsCoordinateTransform(crs_source, crs_dest, transformContext)
            start_point = tf.transform(start_point)
            end_point = tf.transform(end_point)

        # Сопоставляем точкам начала и конца маршрута ближайшие узлы
        start_node = ox.distance.nearest_nodes(G, start_point.x(), start_point.y(), return_dist=False)
        end_node = ox.distance.nearest_nodes(G, end_point.x(), end_point.y(), return_dist=False)


        # Ищем кратчайший маршрут
        # route = nx.shortest_path(G, source=start_node, target=end_node, weight=travel_time_field)
        # route = ox.routing.shortest_path(G, start_node, end_node)
        route = nx.dijkstra_path(G, source=start_node, target=end_node, weight=travel_time_field)
        feedback.setProgress(95)

        

        # Сохраняем в итоговый слой
        route_gdf = ox.routing.route_to_gdf(G, route)
        ## Сохранение
        route_gdf.to_file(target_file)
        
        # Вывод сведения о протяженности имаршрута
        total_len = route_gdf[travel_time_field].sum()
        feedback.pushInfo(f'Время следования по маршруту: {total_len} мин.')

        # Добавляем полученный слой на карту
        vlayer = QgsVectorLayer(target_file, layer_name, 'ogr')
        QgsProject.instance().addMapLayer(vlayer)

        
        feedback.setProgress(100)
        return {self.OUTPUT: target_file}

