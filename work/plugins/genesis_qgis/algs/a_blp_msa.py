"""
Определение оптимального размещения единственного подразделения
"""

import os


import networkx as nx
import osmnx as ox
import geopandas as gpd
import pandas as pd
from shapely import unary_union



# from shapely.geometry import Polygon, box
# from shapely.wkt import loads


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
                       QgsProcessingParameterNumber,
                       QgsProcessingParameterField,
                       QgsProcessingParameterEnum,
                       QgsProcessingParameterFeatureSource,
                       QgsProcessingParameterBoolean,
                       QgsProcessingParameterDefinition,
                       QgsCoordinateReferenceSystem,
                       QgsCoordinateTransform,
                       )

from genesis.metrics import ArrivalTime, CoverIndex
from genesis.states import FirstArrivalUnitState
from graphs.speeds import kmh_to_mm, set_graph_travel_times
from graphs.algorithms import graph_rise_from_gpkg
from genesis.best_points import BestNodeMonkey, BestNodesHalfDiameter
from fire_units.metrics import ArrivalTimeBuilding, CoverIndexBuilding

from ..graph_tools import check_file_exists

# На будущее - добавление иконок
pluginPath = os.path.split(os.path.split(os.path.dirname(__file__))[0])[0]



class BLPMSAAlgorithm(QgsProcessingAlgorithm):
    """
    Расчет кратчайшего маршрута между двумя точками.
    """

    INPUT              = 'INPUT'
    TARGET_POINTS      = 'TARGET_POINTS'
    AREA_POLYGON_LAYER = 'AREA_POLYGON_LAYER'
    SPEEDS             = 'SPEEDS'
    TRAVEL_TIME_FIELD  = 'TRAVEL_TIME_FIELD'

    OPTIMIZED_METRIC   = 'OPTIMIZED_METRIC'
    GLOBAL_JUMPS       = 'GLOBAL_JUMPS'
    LOCAL_JUMPS        = 'LOCAL_JUMPS'
    JUMP_DISTANCE      = 'JUMP_DISTANCE'

    RESULT_LAYER_NAME  = 'RESULT_LAYER_NAME'
    SIMPLIFY           = 'SIMPLIFY'
    OUTPUT             = 'OUTPUT'

    PRE_GDS_PATH       = '{}.ml'

    # Сделать иконку
    # def icon(self):
    #     return QIcon(os.path.join(pluginPath, 'genesis_qgis', 'icons', 'flag.svg'))


    def tr(self, string):
        """
        Возвращает перевод для self.tr().
        """
        return QCoreApplication.translate('Processing', string)

    def createInstance(self):
        return BLPMSAAlgorithm()

    def name(self):
        """
        Название алгоритма
        """
        return 'a_blp_msa'

    def displayName(self):
        """
        Отображаемое в списке имя алгоритма
        """
        return self.tr('Обезьяний поиск (MSA)')

    def group(self):
        """
        Отображаемое в списке имя группы
        """
        return self.tr('Оптимальное размещение 1 подразделения')

    def groupId(self):
        """
        ID группы алгоритмов
        """
        return 'BLP'

    def shortHelpString(self):
        """
        Строка подсказки
        """
        return self.tr(
            '''
            Расчет оптимального размещения единственного подразделения.

            Используется алгоритм обезьяньего поиска.
            '''
            )

    def initAlgorithm(self, config=None):
        """
        Здесь указываются настройки алгоритма - входы и выходы.
        Все это будет указываться в окне интерфейса алгоритма.
        """

        # Слой дорожной сети
        self.addParameter(QgsProcessingParameterFeatureSource (
            self.INPUT, self.tr('Слой улично-дорожной сети'),[QgsProcessing.TypeVectorLine]
            ))
        # Целевой слой прибытия
        self.addParameter(QgsProcessingParameterFeatureSource (
            self.TARGET_POINTS, self.tr('Целевой слой прибытия (если не указан, рассчитывается для узлов графа)'),
            [QgsProcessing.TypeVectorPoint, QgsProcessing.TypeVectorPolygon],
            optional=True,
            ))
        # Слой границ расчетной области
        self.addParameter(QgsProcessingParameterFeatureSource (
            self.AREA_POLYGON_LAYER, self.tr('Границы расчетной области (если указан, будут рассмотрены все объекты в слое)'),
            [QgsProcessing.TypeVectorPoint, QgsProcessing.TypeVectorPolygon],
            optional=True,
            ))
        # Целевая метрика для оптимизации
        self.addParameter(QgsProcessingParameterEnum(
            self.OPTIMIZED_METRIC,
            self.tr('Целевая метрика'),
            [
                self.tr('Среднее время прибытия'),
                self.tr('ИП-10'),
                self.tr('ИП-20'),
            ],
            defaultValue=0
            ))
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

        # Дополнительные параметры алгоритма
        params = []
        params.append(QgsProcessingParameterNumber(self.GLOBAL_JUMPS,
                                                   self.tr('Глобальных прыжков'),
                                                   QgsProcessingParameterNumber.Integer,
                                                   1, False, 0, 10))
        params.append(QgsProcessingParameterNumber(self.LOCAL_JUMPS,
                                                   self.tr('Локальных прыжков'),
                                                   QgsProcessingParameterNumber.Integer,
                                                   10, False, 1, 100))
        params.append(QgsProcessingParameterNumber(self.JUMP_DISTANCE,
                                                   self.tr('Дистанция локального прыжка'),
                                                   QgsProcessingParameterNumber.Integer,
                                                   1000, False, 50, 100000))
        for p in params:
            p.setFlags(p.flags() | QgsProcessingParameterDefinition.FlagAdvanced)
            self.addParameter(p)

        # Поле названия итогового слоя
        self.addParameter(QgsProcessingParameterString (
            self.RESULT_LAYER_NAME, self.tr('Имя итогового слоя'), 'Оптимальное размещение'
            ))
        # Выходной слой
        self.addParameter(QgsProcessingParameterFileDestination(
                self.OUTPUT, self.tr('Выходной файл'), 'файл Geopackage (*.gpkg)',
            ))



    def processAlgorithm(self, parameters, context, feedback):
        """
        Код алгоритма
        """
        def after_local_jump(local_jump_number, best_metric, best_metric_current, **kwargs):
            feedback.pushDebugInfo(f'# {local_jump_number}) значение целевой метрики: {best_metric}. Текущая {best_metric_current}')


        travel_time_field = 'travel_time'


        feedback.pushDebugInfo('Версии библиотек:')
        feedback.pushDebugInfo(f'   osmnx: {ox.__version__}')
        feedback.pushDebugInfo(f'   networkx: {nx.__version__}')
        feedback.pushDebugInfo(f'   geopandas: {gpd.__version__}')

        # Получение исходных параметров алгоритма
        ## Дорожная сеть
        network = self.parameterAsVectorLayer(parameters, self.INPUT, context)
        if network is None:
            raise QgsProcessingException(self.invalidSourceError(parameters, self.INPUT))
        crs = self.parameterAsExtentCrs(parameters, self.INPUT, context)

        target_points_layer = self.parameterAsVectorLayer(parameters, self.TARGET_POINTS, context)
        area_layer          = self.parameterAsVectorLayer(parameters, self.AREA_POLYGON_LAYER, context)

        optimized_metric    = self.parameterAsEnum(parameters, self.OPTIMIZED_METRIC, context)

        simplify          = self.parameterAsBoolean(parameters, self.SIMPLIFY, context)
        speeds            = self.parameterAsMatrix(parameters, self.SPEEDS, context)[1::2]
        speeds            = [float(s) for s in speeds]
        result_layer_name = self.parameterAsString(parameters, self.RESULT_LAYER_NAME, context)
        target_file       = self.parameterAsFile(parameters, self.OUTPUT, context)
        
        # Параметры алгоритма
        global_jumps       = self.parameterAsInt(parameters, self.GLOBAL_JUMPS, context)
        local_jumps       = self.parameterAsInt(parameters, self.LOCAL_JUMPS, context)
        jump_distance     = self.parameterAsInt(parameters, self.JUMP_DISTANCE, context)


        # ================================================================================================
        # Тело алгоритма
        feedback.setProgress(5)

        # Подготовка графа дорожной сети
        pre_gds_file = self.PRE_GDS_PATH.format(network.id())
        if check_file_exists(pre_gds_file):
            # Загружаем граф
            feedback.pushDebugInfo('Используем предварительно скомпилированный ГДС')
            feedback.setProgressText('Загружаем граф дорожной сети')
            G = ox.load_graphml(pre_gds_file)
            roads_gdf = ox.graph_to_gdfs(G, nodes=False)
        else:
            # Формируем граф дорожной сети
            feedback.setProgressText('Формируем граф дорожной сети')
            # Загружаем данные из слоя дорог
            roads_gdf        = gpd.GeoDataFrame.from_features(list(network.getFeatures()), crs=network.sourceCrs().authid())
            ## Проверяем наличие нужных полей
            columns_list = ['highway', 'oneway', 'lanes', 'reversed']
            for col in columns_list:
                if not col in roads_gdf.columns:
                    raise QgsProcessingException(f'Поле {col} отсутствует в списке полей входящего слоя дорожной сети!')
            ## Реконструкция графа
            G = graph_rise_from_gpkg(roads_gdf,
                                    columns_list = columns_list)
            if simplify:
                feedback.setProgress(40)
                feedback.setProgressText('Упрощаем граф дорожной сети')
                G = ox.simplify_graph(G)

        ## Установка скоростей следования
        set_graph_travel_times(G, speeds, morph_function=kmh_to_mm, travel_time_field=travel_time_field)
        ## Вывод
        g_crs = G.graph['crs']
        feedback.pushInfo(f'Получен граф дорог с количеством узлов - {G.number_of_nodes()} и ребер {G.number_of_edges()}. СК: {g_crs}')
        feedback.setProgress(40)



        # Подготавливаем геодатасеты
        feedback.setProgressText('Подготавливаем данные')
        if target_points_layer:
            target_points_gdf = gpd.GeoDataFrame.from_features(list(target_points_layer.getFeatures()), crs=target_points_layer.sourceCrs().authid())
        else:
            target_points_gdf = None
        if area_layer:
            area_gdf = gpd.GeoDataFrame.from_features(list(area_layer.getFeatures()), crs=area_layer.sourceCrs().authid())
        else:
            area_gdf = None
        feedback.setProgress(50)


        # Приводим все GeoDataFrame к единой СК
        feedback.setProgressText('Приводим все данные к единой СК')
        estimated_utm_crs = roads_gdf.estimate_utm_crs()
        # if roads_gdf.crs != estimated_utm_crs: roads_gdf = ox.project_gdf(roads_gdf, to_crs=estimated_utm_crs)
        if target_points_layer:
            if target_points_gdf.crs != estimated_utm_crs: target_points_gdf = ox.projection.project_gdf(target_points_gdf, to_crs=estimated_utm_crs)
        if area_layer:
            if area_gdf.crs != estimated_utm_crs: area_gdf = ox.projection.project_gdf(area_gdf, to_crs=estimated_utm_crs)
        feedback.setProgress(55)

        


        # Расчет
        feedback.setProgressText('Расчет размещения')

        ## Проецируем граф
        G = ox.projection.project_graph(G)

        ## Определяем область для расчета, если передан area_layer (и получен area_gdf)
        if not area_gdf is None:
            area_poly   = unary_union(area_gdf.geometry)
            g_nodes_gdf = ox.graph_to_gdfs(G, edges=False)
            area        = g_nodes_gdf.within(area_poly)
            # Если также передан целевой слой, дополнительно обрезаем и его
            if not target_points_gdf is None:
                target_points_gdf = target_points_gdf[target_points_gdf.within(area_poly)]
        else:
            area = None

        ## Определение стартового узла
        Warning    ('Сейчас выбирается узел по середине диаметра')
        bnhd       = BestNodesHalfDiameter()
        start_node = bnhd(env=G)

        ## Определяем объекты алгоритма
        metric_func = None
        if target_points_gdf is None:
            if optimized_metric   == 0:
                metric_func  = ArrivalTime()
            elif optimized_metric == 1:
                metric_func  = CoverIndex()
            elif optimized_metric == 2:
                metric_func  = CoverIndex(20)
        else:
            centroids                 = target_points_gdf.geometry.centroid
            target_points_gdf['node'] = ox.nearest_nodes(G, centroids.x, centroids.y)
            if optimized_metric   == 0:
                metric_func = ArrivalTimeBuilding(target_points_gdf)
            elif optimized_metric == 1:
                metric_func =  CoverIndexBuilding(target_points_gdf)
            elif optimized_metric == 2:
                metric_func  = CoverIndexBuilding(target_points_gdf, ip_val=20)
        bnmsa = BestNodeMonkey(FirstArrivalUnitState(),
                               metric_function           = metric_func,
                               global_jumps_count        = global_jumps,
                               local_jumps_count         = local_jumps,
                               local_jump_max_distance   = jump_distance,
                               after_local_jump_function = after_local_jump)
        ## Проводим расчет
        feedback.setProgressText('Расчет оптимального размещения')
        best_node, best_metric = bnmsa(env         = G,
                                        area       = area,
                                        start_node = start_node)
        best_nodes = {best_node: 'Оптимум'}
        # feedback.pushWarning(f'Среднее время прибытия:     {round(best_metric,1)} мин.')
        feedback.setProgress(90)







        ## Вычисляем результирующие метрики
        times, nearest = FirstArrivalUnitState()(env=G, points=best_nodes, area=area)

        # Вычисляем основные метрики
        if target_points_gdf is None:
            arr_time_mean = round(ArrivalTime()(times), 1)
            ip10 = round(CoverIndex()(times), 1)
            ip20 = round(CoverIndex(20)(times), 1)
        else:
            arr_time_mean = round(ArrivalTimeBuilding(target_points_gdf)(times), 1)
            ip10 = round(CoverIndexBuilding(target_points_gdf)(times), 1)
            ip20 = round(CoverIndexBuilding(target_points_gdf, ip_val=20)(times), 1)
        feedback.pushWarning('Результирующие метрики:')
        feedback.pushWarning(f'Среднее время прибытия:     {arr_time_mean} мин.')
        feedback.pushWarning(f'Индекс прикрытия 10 мин:    {ip10} %')
        feedback.pushWarning(f'Индекс прикрытия 20 мин:    {ip20} %')
        feedback.setProgress(95)

        # Формирование итоговых слоев
        feedback.setProgressText('Формирование итоговых слоев')
        # Перепроецируем датасет маршрутов в СК дорожной сети
        result_gdf = ox.graph_to_gdfs(G, edges=False).loc[[best_node]]
        result_gdf.loc[best_node, 'Время прибытия среднее'] = arr_time_mean
        result_gdf.loc[best_node, 'ИП-10'] = ip10
        result_gdf.loc[best_node, 'ИП-20'] = ip20

        result_gdf = ox.projection.project_gdf(result_gdf, to_crs=crs.authid())

        # Сохраняем в итоговый слой
        result_gdf.to_file(target_file)

        # Добавляем полученный слой на карту
        vlayer = QgsVectorLayer(target_file, result_layer_name, 'ogr')
        QgsProject.instance().addMapLayer(vlayer)


        feedback.setProgress(100)
        return {self.OUTPUT: target_file}


