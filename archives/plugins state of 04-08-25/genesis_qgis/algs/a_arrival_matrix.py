"""
Расчет кратчайшего маршрута между двумя точками
"""

import os

import numpy as np
import networkx as nx
import osmnx as ox
import geopandas as gpd
import pandas as pd
from shapely import unary_union



# from shapely.geometry import Polygon, box
# from shapely.wkt import loads


from qgis.PyQt.QtCore import QCoreApplication
from qgis.PyQt.QtGui import QIcon

from qgis.core import (
                       QgsProject,
                       QgsVectorLayer,
                       QgsProcessingException,
                       QgsProcessingAlgorithm,
                       QgsProcessing,
                       QgsProcessingParameterFileDestination,
                       QgsProcessingParameterMatrix,
                       QgsProcessingParameterString,
                       QgsProcessingParameterFeatureSource,
                       QgsProcessingParameterBoolean,
                       QgsProcessingParameterDefinition,
                       )

from genesis.metrics import ArrivalTime, CoverIndex
from genesis.states import FirstArrivalUnitState
from graphs.speeds import kmh_to_mm, set_graph_travel_times
from graphs.algorithms import graph_rise_from_gpkg

from ..graph_tools import check_file_exists


pluginPath = os.path.split(os.path.split(os.path.dirname(__file__))[0])[0]



class ArrivalMatrixAlgorithm(QgsProcessingAlgorithm):
    """
    Расчет матрицы прибытия всех пожарных подразделений
    ко всем целевым объектам
    """

    INPUT                = 'INPUT'
    START_POINTS         = 'START_POINTS'
    TARGET_POINTS        = 'TARGET_POINTS'
    AREA_POLYGON_LAYER   = 'AREA_POLYGON_LAYER'
    SPEEDS               = 'SPEEDS'
    TRAVEL_TIME_FIELD    = 'TRAVEL_TIME_FIELD'
    RESULT_LAYER_NAME    = 'RESULT_LAYER_NAME'
    SIMPLIFY             = 'SIMPLIFY'

    ADD_UNITS_TIMES      = 'ADD_UNITS_TIMES'
    ADD_UNITS_DISTANCE   = 'ADD_UNITS_DISTANCE'
    ADD_NEAREST_UNIT     = 'ADD_NEAREST_UNIT'
    ADD_NEAREST_TIME     = 'ADD_NEAREST_TIME'
    ADD_NEAREST_DISTANCE = 'ADD_NEAREST_DISTANCE'
    ADD_TIME_OVERLAY     = 'ADD_TIME_OVERLAY'
    ADD_DISTANCE_OVERLAY = 'ADD_DISTANCE_OVERLAY'

    OUTPUT               = 'OUTPUT'

    PRE_GDS_PATH         = '{}.ml'


    # Сделать иконку
    # def icon(self):
    #     return QIcon(os.path.join(pluginPath, 'genesis_qgis', 'icons', 'icon_dijkstra_onetoone.svg'))


    def tr(self, string):
        """
        Возвращает перевод для self.tr().
        """
        return QCoreApplication.translate('Processing', string)

    def createInstance(self):
        return ArrivalMatrixAlgorithm()

    def name(self):
        """
        Название алгоритма
        """
        return 'a_arrival_matrix'

    def displayName(self):
        """
        Отображаемое в списке имя алгоритма
        """
        return self.tr('Расчет матрицы прибытия')

    def group(self):
        """
        Отображаемое в списке имя группы
        """
        return self.tr('Моделирование')

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
            Расчет матрицы прибытия всех пожарных подразделений
            ко всем целевым объектам (<i>или в узлы ГДС</i>).
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
        # Работаем с упрощенным графом или нет
        self.addParameter(QgsProcessingParameterBoolean(self.SIMPLIFY, self.tr('Упростить граф'), True))
        # Слой стартовых точек
        self.addParameter(QgsProcessingParameterFeatureSource (
            self.START_POINTS, self.tr('Размещение пожарных подразделений'), [QgsProcessing.TypeVectorPoint],
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
        

        # Дополнительные параметры алгоритма
        params = []
        params.append(QgsProcessingParameterBoolean(
            self.ADD_UNITS_TIMES, self.tr('Добавить времена прибытия всех подразделений'), True))
        params.append(QgsProcessingParameterBoolean(
            self.ADD_UNITS_DISTANCE, self.tr('Добавить расстояния до всех подразделений'), False))
        params.append(QgsProcessingParameterBoolean(
            self.ADD_NEAREST_UNIT, self.tr('Добавить ближайшее подразделение'), True))
        params.append(QgsProcessingParameterBoolean(
            self.ADD_NEAREST_TIME, self.tr('Добавить время прибытия ближайшего подразделения'), True))
        params.append(QgsProcessingParameterBoolean(
            self.ADD_NEAREST_DISTANCE, self.tr('Добавить расстояние до ближайшего подразделения'), False))
        # params.append(QgsProcessingParameterBoolean(
        #     self.ADD_TIME_OVERLAY, self.tr('Добавить перекрытие по времени'), False))
        # params.append(QgsProcessingParameterBoolean(
        #     self.ADD_DISTANCE_OVERLAY, self.tr('Добавить перекрытие по расстоянию'), False))
        for p in params:
            p.setFlags(p.flags() | QgsProcessingParameterDefinition.FlagAdvanced)
            self.addParameter(p)



        # Итоговые параметры
        # Поле названия итогового слоя
        self.addParameter(QgsProcessingParameterString (
            self.RESULT_LAYER_NAME, self.tr('Имя итогового слоя'), 'Время прибытия'
            ))
        # Выходной слой
        self.addParameter(QgsProcessingParameterFileDestination(
                self.OUTPUT, self.tr('Выходной файл'), 'файл Geopackage (*.gpkg)',
            ))



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
        ## Дорожная сеть
        network = self.parameterAsVectorLayer(parameters, self.INPUT, context)
        if network is None:
            raise QgsProcessingException(self.invalidSourceError(parameters, self.INPUT))
        crs = self.parameterAsExtentCrs(parameters, self.INPUT, context)

        start_points_layer  = self.parameterAsVectorLayer(parameters, self.START_POINTS, context)
        target_points_layer = self.parameterAsVectorLayer(parameters, self.TARGET_POINTS, context)
        area_layer          = self.parameterAsVectorLayer(parameters, self.AREA_POLYGON_LAYER, context)


        simplify          = self.parameterAsBoolean(parameters, self.SIMPLIFY, context)
        speeds            = self.parameterAsMatrix(parameters, self.SPEEDS, context)[1::2]
        speeds            = [float(s) for s in speeds]

        # Что добавляем
        add_units_times    = self.parameterAsBoolean(parameters, self.ADD_UNITS_TIMES, context)
        add_units_distance = self.parameterAsBoolean(parameters, self.ADD_UNITS_DISTANCE, context)
        add_nearest_unit   = self.parameterAsBoolean(parameters, self.ADD_NEAREST_UNIT, context)
        add_nearest_time   = self.parameterAsBoolean(parameters, self.ADD_NEAREST_TIME, context)
        add_nearest_distance = self.parameterAsBoolean(parameters, self.ADD_NEAREST_DISTANCE, context)

        if add_units_times + add_units_distance + add_nearest_unit + add_nearest_time + add_nearest_distance == 0:
            raise QgsProcessingException('Необходимо выбрать хотя бы один параметр для добавления!')


        result_layer_name = self.parameterAsString(parameters, self.RESULT_LAYER_NAME, context)
        target_file       = self.parameterAsFile(parameters, self.OUTPUT, context)


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
            columns_list = ['highway', 'oneway', 'lanes']
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
        start_points_gdf = gpd.GeoDataFrame.from_features(list(start_points_layer.getFeatures()), crs=start_points_layer.sourceCrs().authid())
        if not 'name' in start_points_gdf.columns:
            raise QgsProcessingException(f'Поле "name" отсутствует в списке полей входящего слоя подразделений!')
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
        if start_points_gdf.crs != estimated_utm_crs: start_points_gdf = ox.projection.project_gdf(start_points_gdf, to_crs=estimated_utm_crs)
        if target_points_layer:
            if target_points_gdf.crs != estimated_utm_crs: target_points_gdf = ox.projection.project_gdf(target_points_gdf, to_crs=estimated_utm_crs)
        if area_layer:
            if area_gdf.crs != estimated_utm_crs: area_gdf = ox.projection.project_gdf(area_gdf, to_crs=estimated_utm_crs)
        feedback.setProgress(55)



        # ===================================================================================================
        # Расчет
        feedback.setProgressText('Расчет времен следования')

        # ## Проецируем граф
        # G = ox.projection.project_graph(G)

        # ## Определение узлов размещения ПСЧ
        # nodes_nn = ox.nearest_nodes(G, start_points_gdf.geometry.x, start_points_gdf.geometry.y)
        # start_points_gdf['node'] = nodes_nn
        # start_points_dict = {node:name for name, node in zip(start_points_gdf['name'], start_points_gdf['node'])}
        
        # Сопоставление подразделений с узлами графов
        # Узлы графа
        g_nodes = ox.graph_to_gdfs(G, edges=False)

        # Сопоставляем точки ПСЧ с узлами графа
        start_points_gdf = ox.projection.project_gdf(start_points_gdf).sjoin_nearest(ox.projection.project_gdf(g_nodes))
        start_points_gdf = ox.projection.project_gdf(start_points_gdf, to_latlong=True)
        start_points_gdf = start_points_gdf.rename(columns={'osmid': 'node'})
        start_points_gdf = start_points_gdf.set_index('name')    #['node'].to_dict()


        # Определяем область для расчета, если передан area_layer (и получен area_gdf)
        # if not area_gdf is None:
        #     area_poly = unary_union(area_gdf.geometry)
        #     g_nodes_gdf = ox.graph_to_gdfs(G, edges=False)
        #     area = g_nodes_gdf.within(area_poly)
        #     # Если также передан целевой слой, дополнительно обрезаем и его
        #     if not target_points_gdf is None:
        #         target_points_gdf = target_points_gdf[target_points_gdf.within(area_poly)]
        # else:
        #     area = None

        if not area_gdf is None:
            inner_nodes = g_nodes.sjoin(area_gdf).copy()
        else:
            inner_nodes = g_nodes
        inner_nodes_list = g_nodes.index




        # Производим расчет
        for unit, unit_data in start_points_gdf.iterrows():
            feedback.pushInfo(f'Расчет для {unit}')
            # print(unit_data['node'])
            paths = nx.shortest_path(
                G,
                source = unit_data['node'],
                weight = travel_time_field,
            )
            # path_length = nx.shortest_path_length(
            #     G,
            #     source = unit_data['node'].iloc[0],
            #     weight = travel_time_field,
            # )
            # path_length = {k:v for k,v in path_length.items() if k in inner_nodes_list}
            # path_length_s = pd.Series(path_length, name=unit)
            paths = {k:v for k,v in paths.items() if k in inner_nodes_list}

            # if add_units_times:

            # Определение расстояний от каждой из ПСЧ
            feedback.pushInfo(f'граф дорог с количеством узлов - {G.number_of_nodes()} и ребер {G.number_of_edges()}')
            if add_units_distance:
                path_length = {k: ox.routing.route_to_gdf(G, v)['length'] for k,v in paths.items()}
                path_length_s = pd.Series(path_length, name=unit)
                inner_nodes = inner_nodes.merge(path_length_s, left_index=True, right_index=True)
        
        # Расчет дополнительных параметров
        def count_if(data, val):
            return (data <= val).sum()

        # Предварительный расчет ближайшей ПСЧ и расстояния до нее
        inner_nodes['nearest_distance'] = np.min(inner_nodes[list(target_points_gdf.index)], axis=1)
        inner_nodes['nearest_unit'] = np.argmin(inner_nodes[list(target_points_gdf.index)], axis=1)
        inner_nodes['nearest_unit'] = inner_nodes['nearest_unit'].replace(
            {k:v for k,v in enumerate(target_points_gdf.index)}
        )
        # inner_nodes['arrival_in_10'] = inner_nodes[list(target_points_gdf.index)].apply(count_if, val=10, axis=1)



        # Приведение к итоговой переменной
        result_gdf = inner_nodes

        # Вычисляем основные метрики
        # arr_time_mean = round(ArrivalTime()(result_gdf['first_unit_time']), 1)
        # ip10 = round(CoverIndex()(result_gdf['first_unit_time']), 1)
        # ip20 = round(CoverIndex(20)(result_gdf['first_unit_time']), 1)
        # feedback.pushWarning(f'Среднее время прибытия:     {arr_time_mean} мин.')
        # feedback.pushWarning(f'Индекс прикрытия 10 мин:    {ip10} %')
        # feedback.pushWarning(f'Индекс прикрытия 20 мин:    {ip20} %')
        feedback.setProgress(90)

        # Формирование итоговых слоев
        feedback.setProgressText('Формирование итоговых слоев')
        # Перепроецируем датасет маршрутов в СК дорожной сети
        result_gdf = ox.projection.project_gdf(result_gdf, to_crs=crs.authid())

        # Сохраняем в итоговый слой
        result_gdf.to_file(target_file)

        # Добавляем полученный слой на карту
        vlayer = QgsVectorLayer(target_file, result_layer_name, 'ogr')
        QgsProject.instance().addMapLayer(vlayer)


        feedback.setProgress(100)
        return {self.OUTPUT: target_file}
