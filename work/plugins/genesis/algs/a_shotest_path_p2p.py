"""
Расчет кратчайшего маршрута между двумя точками
"""

import os


import networkx as nx
import osmnx as ox
import geopandas as gpd
from shapely import unary_union
# from shapely.ops import unary_union

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
                       QgsProcessingParameterMatrix,
                    #    QgsProcessingParameterExtent,
                       QgsProcessingParameterString,
                       QgsProcessingParameterPoint,
                       QgsProcessingParameterField,
                       QgsProcessingParameterEnum,
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
    SPEEDS = 'SPEEDS'
    START_POINT = 'START_POINT'
    END_POINT = 'END_POINT'
    TRAVEL_TIME_FIELD = 'TRAVEL_TIME_FIELD'
    RESULT_FIELD = 'RESULT_FIELD'
    SIMPLIFY = 'SIMPLIFY'
    RESULT_TYPE = 'RESULT_TYPE'
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

        self.RESULT_TYPE_LIST = [self.tr('Дискретный маршрут (отдельные линии для каждого участка)'),
                            self.tr('Сплошной маршрут (единая линия для всего маршрута)')]

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
        # Расчетные скорости следования
        self.addParameter(
            QgsProcessingParameterMatrix (
                self.SPEEDS,
                self.tr('Расчетные скорости следования'),
                numberRows = 5,
                hasFixedNumberRows=True,
                headers = [self.tr('Дорога'), self.tr('Скорость')],
                defaultValue = [
                'Магистральные городские дороги и улицы общегородского значения', 49,
                'Магистральные улицы районного значения', 37,
                'Улицы и дороги местного значения', 26,
                'Служебные проезды: внутриквартальные, въездные, парковочные и т.д.', 16,
                'Пешеходные зоны и территории пригодные для передвижения пожарных автомобилей', 5
                ]
            )
        )
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
        # Тип результата (список)
        self.addParameter(QgsProcessingParameterEnum(self.RESULT_TYPE,
                                                     self.tr('Представление результата'),
                                                     self.RESULT_TYPE_LIST,
                                                     defaultValue=0))
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
        simplify = self.parameterAsBoolean(parameters, self.SIMPLIFY, context)
        speeds = self.parameterAsMatrix(parameters, self.SPEEDS, context)[1::2]
        speeds = [float(s) for s in speeds]
        result_types = self.parameterAsEnum(parameters, self.RESULT_TYPE, context) #int

        # В дальнейшем нужно передавать эти поля явно!
        # highway_field = self.parameterAsString(parameters, self.HIGHWAY_FIELD, context)
        # oneway_field = self.parameterAsString(parameters, self.ONEWAY_FIELD, context)
        # lanes_field = self.parameterAsString(parameters, self.LANES_FIELD, context)
        # reversed_field = self.parameterAsString(parameters, self.REVERSED_FIELD, context)
        
        
        layer_name = self.parameterAsString(parameters, self.RESULT_FIELD, context)
        target_file = self.parameterAsFile(parameters, self.OUTPUT, context)

        # Тело алгоритма
        feedback.setProgress(5)
        # Подготавливаем геодатасет с геометрией дорог
        roads = gpd.GeoDataFrame.from_features(list(network.getFeatures()), crs=crs.authid())
        try:
            roads = ox.project_gdf(roads)
        except:
            feedback.pushInfo('Перепроецирование слоя улично-дорожной сети не требуется')
        feedback.setProgress(30)

        columns_list = ['name', 'highway', 'oneway', 'lanes', 'reversed']
        for col in columns_list:
            if not col in roads.columns:
                raise QgsProcessingException(f'Поле {col} отсутствует в списке полей входящего слоя дорожной сети!')


        # Формируем граф
        G = graph_rise_from_gpkg(roads,
                                 columns_list = columns_list)
        if simplify:
            G = ox.simplify_graph(G)
        g_crs = G.graph['crs']
        feedback.pushInfo(f'Получен граф дорог с количеством узлов - {G.number_of_nodes()} и ребер {G.number_of_edges()}. СК: {g_crs}')
        feedback.setProgress(70)

        # Устанавливаем скорости следования
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
        route = nx.dijkstra_path(G, source=start_node, target=end_node, weight=travel_time_field)
        feedback.setProgress(95)

        
        # Получаем геодатафрейм пути
        route_gdf = ox.routing.route_to_gdf(G, route)
        # Вывод сведения о протяженности имаршрута
        total_len = route_gdf[travel_time_field].sum()
        feedback.pushInfo(f'Время следования по маршруту: {total_len} мин.')

        # Перепроецируем датасет маршрутов в СК дорожной сети
        route_gdf = ox.project_gdf(route_gdf, to_crs=crs.authid())

        # Сохраняем в итоговый слой
        if result_types == 0:
            route_gdf.to_file(target_file)
        elif result_types == 1:
            full_route_geometry = unary_union(route_gdf.geometry)

            d = {travel_time_field: [total_len], 'geometry': [full_route_geometry]}
            new_gdf = gpd.GeoDataFrame(d, crs=route_gdf.crs)
            new_gdf.to_file(target_file)

        # Добавляем полученный слой на карту
        vlayer = QgsVectorLayer(target_file, layer_name, 'ogr')
        QgsProject.instance().addMapLayer(vlayer)

        
        feedback.setProgress(100)
        return {self.OUTPUT: target_file}

