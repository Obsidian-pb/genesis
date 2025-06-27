"""
Определение оптимального размещения n подразделений
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

from genesis.states import FirstArrivalUnitState, get_atm
from graphs.speeds import kmh_to_mm, set_graph_travel_times
from graphs.algorithms import graph_rise_from_gpkg
from genesis.metrics import ArrivalTime, CoverIndex, CoverIndexValue
from fire_units.metrics import ArrivalTimeBuilding, CoverIndexBuilding
from genesis.lscp import LSCP_ADD

from ..graph_tools import check_file_exists

# На будущее - добавление иконок
pluginPath = os.path.split(os.path.split(os.path.dirname(__file__))[0])[0]



class BLPADDlgorithm(QgsProcessingAlgorithm):
    """
    Алгоритм расчета мест размещения заданного количества подразделений.
    """

    INPUT              = 'INPUT'
    TARGET_LAYER       = 'TARGET_LAYER'
    EXISTED_UNITS      = 'EXISTED_UNITS'
    AREA_POLYGON_LAYER = 'AREA_POLYGON_LAYER'
    SPEEDS             = 'SPEEDS'
    TRAVEL_TIME_FIELD  = 'TRAVEL_TIME_FIELD'
    WEIGHT             = 'WEIGHT'

    OPTIMIZED_METRIC   = 'OPTIMIZED_METRIC'
    #GLOBAL_JUMPS       = 'GLOBAL_JUMPS'
    #LOCAL_JUMPS        = 'LOCAL_JUMPS'
    #JUMP_DISTANCE      = 'JUMP_DISTANCE'

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
        return BLPADDlgorithm()

    def name(self):
        """
        Название алгоритма
        """
        return 'a_blp_msa'

    def displayName(self):
        """
        Отображаемое в списке имя алгоритма
        """
        return self.tr('Жадное добавление')

    def group(self):
        """
        Отображаемое в списке имя группы
        """
        return self.tr('Оптимальное размещение n подразделений')

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

            Используется алгоритм жадного добавления.
            '''
            )

    def initAlgorithm(self, config=None):
        """
        Здесь указываются настройки алгоритма - входы и выходы.
        Все это будет указываться в окне интерфейса алгоритма.
        """

        # Слой улично-дорожной сети
        self.addParameter(QgsProcessingParameterFeatureSource (
            self.INPUT, self.tr('Слой улично-дорожной сети'),[QgsProcessing.TypeVectorLine]
            ))
        # # Поле веса ребер графа
        # self.addParameter(QgsProcessingParameterField(
        #     'WEIGHT',
        #     self.tr('Поле веса ребер графа'),
        #     parentLayerParameterName=self.INPUT,
        #     type=QgsProcessingParameterField.Numeric,
        #     defaultValue='travel_time',            
        #     optional=False
        # ))
        # Количество размещаемых подразделений
        self.addParameter(QgsProcessingParameterNumber(
            'TARGET_UNITS_COUNT',
            self.tr('Количество размещаемых подразделений'),
            QgsProcessingParameterNumber.Integer,
            defaultValue=1,
            optional=False
        ))
        # Целевой слой прибытия
        self.addParameter(QgsProcessingParameterFeatureSource (
            self.TARGET_LAYER, self.tr('Целевой слой прибытия (например, здания))'),
            [QgsProcessing.TypeVectorPoint, QgsProcessing.TypeVectorPolygon],
            optional=False,
            ))
        # Расчетное время прибытия
        self.addParameter(QgsProcessingParameterNumber(
            'CUTOFF',
            self.tr('Расчетное время прибытия (мин)'),
            QgsProcessingParameterNumber.Integer,
            defaultValue=10,
            optional=False
        ))
        # Слой существующих подразделений
        self.addParameter(QgsProcessingParameterFeatureSource (
            self.EXISTED_UNITS, self.tr('Существующие подразделения'),[QgsProcessing.TypeVectorPoint],
            optional=True,
            ))
        # Слой границ расчетной области
        self.addParameter(QgsProcessingParameterFeatureSource (
            self.AREA_POLYGON_LAYER, self.tr('Границы расчетной области (если указан, будут рассмотрены все объекты в слое)'),
            [QgsProcessing.TypeVectorPoint, QgsProcessing.TypeVectorPolygon],
            optional=True,
            ))
        # Метрика для оценки (возможно имеет смысл убрать...)
        self.addParameter(QgsProcessingParameterEnum(
            self.OPTIMIZED_METRIC,
            self.tr('Метрика'),
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
        # params = []
        # params.append(QgsProcessingParameterNumber(self.GLOBAL_JUMPS,
        #                                            self.tr('Глобальных прыжков'),
        #                                            QgsProcessingParameterNumber.Integer,
        #                                            1, False, 0, 10))
        # params.append(QgsProcessingParameterNumber(self.LOCAL_JUMPS,
        #                                            self.tr('Локальных прыжков'),
        #                                            QgsProcessingParameterNumber.Integer,
        #                                            10, False, 1, 100))
        # params.append(QgsProcessingParameterNumber(self.JUMP_DISTANCE,
        #                                            self.tr('Дистанция локального прыжка'),
        #                                            QgsProcessingParameterNumber.Integer,
        #                                            1000, False, 50, 100000))
        # for p in params:
        #     p.setFlags(p.flags() | QgsProcessingParameterDefinition.FlagAdvanced)
        #     self.addParameter(p)

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
        #def after_local_jump(local_jump_number, best_metric, best_metric_current, **kwargs):
        #    feedback.pushDebugInfo(f'# {local_jump_number}) значение целевой метрики: {best_metric}. Текущая {best_metric_current}')


        DATA_NODE_FIELD     = 'node'
        UNITS_NAME_FIELD    = 'name'


        feedback.pushDebugInfo('Версии библиотек:')
        feedback.pushDebugInfo(f'   osmnx: {ox.__version__}')
        feedback.pushDebugInfo(f'   networkx: {nx.__version__}')
        feedback.pushDebugInfo(f'   geopandas: {gpd.__version__}')

        # 0. Получение исходных параметров алгоритма
        # ================================================================================================
        ## Дорожная сеть
        network = self.parameterAsVectorLayer(parameters, self.INPUT, context)
        if network is None:
            raise QgsProcessingException(self.invalidSourceError(parameters, self.INPUT))
        crs_start           = self.parameterAsExtentCrs(parameters, self.INPUT, context)

        # Получаем количество размещаемых подразделений
        target_units_count  = self.parameterAsInt(parameters, 'TARGET_UNITS_COUNT', context)

        target_layer        = self.parameterAsVectorLayer(parameters, self.TARGET_LAYER, context)
        existed_units_layer = self.parameterAsSource(parameters, self.EXISTED_UNITS, context)
        area_layer          = self.parameterAsVectorLayer(parameters, self.AREA_POLYGON_LAYER, context)

        optimized_metric    = self.parameterAsEnum(parameters, self.OPTIMIZED_METRIC, context)

        simplify            = self.parameterAsBoolean(parameters, self.SIMPLIFY, context)
        speeds              = self.parameterAsMatrix(parameters, self.SPEEDS, context)[1::2]
        speeds              = [float(s) for s in speeds]
        result_layer_name   = self.parameterAsString(parameters, self.RESULT_LAYER_NAME, context)
        target_file         = self.parameterAsFile(parameters, self.OUTPUT, context)
        
        # Получаем поле веса ребер графа
        # weight = self.parameterAsString(parameters, 'WEIGHT', context)

        # Получаем расчетное время прибытия
        cutoff = self.parameterAsDouble(parameters, 'CUTOFF', context)

        # Параметры алгоритма
        # TODO - добавить в параметры алгоритма
        ## Для графа:
        weight              = 'travel_time'
        ## Для матрицы прибытия:
        data_sample_size    = 200
        data_cutoff_field   = None
        target_set          = None

        ## Для ADD:
        ip_val              = 10
        names_pattern       = '{}'
        start_names_index   = 1
        #after_mclp_function = None
        # units_name_field    = 'name'



        # 1. Подготовка исходных данных
        # ================================================================================================
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

        ## Установка скоростей следования
        set_graph_travel_times(G, speeds, 
                               morph_function = kmh_to_mm, 
                               travel_time_field = weight)
        
        ## Упрощение графа
        if not check_file_exists(pre_gds_file):
            if simplify:
                feedback.setProgress(40)
                feedback.setProgressText('Упрощаем граф дорожной сети')
                G = ox.simplify_graph(G)

        ## Проецируем граф в локальную СК
        G = ox.project_graph(G)

        ## Вывод
        estimated_utm_crs = G.graph['crs']
        feedback.pushInfo(f'Получен граф дорог с количеством узлов - {G.number_of_nodes()} и ребер {G.number_of_edges()}. СК: {estimated_utm_crs}')
        feedback.setProgress(40)


        # Подготвока геоданных
        feedback.setProgressText('Подготавливаем данные')
        # Подготовка целевого слоя (здания или точки)
        if target_layer:
            target_layer_gdf = gpd.GeoDataFrame.from_features(
                list(target_layer.getFeatures()),
                crs = target_layer.sourceCrs().authid()
                )
            target_layer_gdf = ox.projection.project_gdf(target_layer_gdf, to_crs=estimated_utm_crs)
            centroids                         = target_layer_gdf.geometry.centroid
            target_layer_gdf[DATA_NODE_FIELD] = ox.nearest_nodes(G, centroids.x, centroids.y)
        else:
            target_layer_gdf = None
        
        # Подготовка слоя существующих подразделений
        if existed_units_layer:
            existed_units_layer_gdf = gpd.GeoDataFrame.from_features(
                list(existed_units_layer.getFeatures()),
                crs = existed_units_layer.sourceCrs().authid()
                )
            existed_units_layer_gdf = ox.projection.project_gdf(existed_units_layer_gdf, to_crs=estimated_utm_crs)
            existed_units_layer_gdf[DATA_NODE_FIELD] = ox.nearest_nodes(G, 
                                                               existed_units_layer_gdf.geometry.x, 
                                                               existed_units_layer_gdf.geometry.y
                                                               )
            if not UNITS_NAME_FIELD in existed_units_layer_gdf.columns:
                existed_units_layer_gdf[UNITS_NAME_FIELD] = pd.Series([f'#{i}' for i in range(len(existed_units_layer_gdf))])
            existed_units_dict = dict(zip(existed_units_layer_gdf[DATA_NODE_FIELD], 
                                          existed_units_layer_gdf[UNITS_NAME_FIELD]))
        else:
            existed_units_layer_gdf = None
            existed_units_dict      = None

        # Подготовка слоя границ расчетной зоны
        if area_layer:
            area_layer_gdf = gpd.GeoDataFrame.from_features(
                list(area_layer.getFeatures()), 
                crs=area_layer.sourceCrs().authid()
                )
            area_layer_gdf = ox.projection.project_gdf(area_layer_gdf, to_crs=estimated_utm_crs)
            g_nodes_gdf    = ox.graph_to_gdfs(G, edges=False)
            points_mask    = g_nodes_gdf.within(unary_union(area_layer_gdf.geometry))
        else:
            area_layer_gdf = None
            points_mask    = None
        feedback.setProgress(50)





        # 2. Расчет
        # ================================================================================================
        ## Расчет матрицы прибытия
        feedback.setProgressText('Расчет матрицы прибытия')
        matrix = get_atm(G,
                 data              = target_layer_gdf,
                 data_sample_size  = data_sample_size,
                 data_node_field   = DATA_NODE_FIELD,
                 weight            = weight,
                 cutoff            = cutoff,
                 data_cutoff_field = data_cutoff_field,
                 target_set        = target_set
                 )
        feedback.setProgress(80)

        # 3. Сборка решения
        # ================================================================================================
        ## Выбор метрики
        metric_func = None
        if target_layer_gdf is None:
            if optimized_metric   == 0:
                metric_func  =  ArrivalTime()
            elif optimized_metric == 1:
                metric_func  =   CoverIndex()
            elif optimized_metric == 2:
                metric_func  = CoverIndex(20)
        else:
            if optimized_metric   == 0:
                metric_func = ArrivalTimeBuilding(target_layer_gdf)
            elif optimized_metric == 1:
                metric_func =  CoverIndexBuilding(target_layer_gdf)
            elif optimized_metric == 2:
                metric_func  = CoverIndexBuilding(target_layer_gdf, ip_val = 20)

        ## Функция обратного вызова при расчете подразделений
        def after_mclp_function(best_metric, dynamic_nodes, **kwargs):
            metric = round(best_metric, 2)
            feedback.pushInfo(f'Подразделений: {len(dynamic_nodes)}, Метрика: {metric}')

        ## Сборка и инициализация алгоритма ADD
        add = LSCP_ADD(  
            state_function      = FirstArrivalUnitState(),
            matrix              = matrix,
            metric_function     = metric_func,
            ip_val              = cutoff,
            stop_case_function  = lambda dynamic_nodes, **kwargs: len(dynamic_nodes) >= target_units_count,
            names_pattern       = names_pattern,
            start_names_index   = start_names_index,
            after_mclp_function = after_mclp_function,
        )

        # 4. Расчет
        # ================================================================================================
        best_nodes, best_metric = add(
            env          = G,
            dynamic_nodes = None,
            static_nodes  = existed_units_dict,
            area          = points_mask,
        )
        best_node = list(best_nodes.keys())[0]
        feedback.setProgress(90)




        # 5. Анализ
        # ================================================================================================
        times, nearest = FirstArrivalUnitState()(env    = G,
                                                 points = best_nodes,
                                                 area   = points_mask)

        # Вычисляем основные метрики
        if target_layer_gdf is None:
            arr_time_mean = round(ArrivalTime()(times), 1)
            ip10 = round(CoverIndex()(times), 1)
            ip20 = round(CoverIndex(20)(times), 1)
        else:
            arr_time_mean = round(ArrivalTimeBuilding(target_layer_gdf)(times), 1)
            ip10 = round(CoverIndexBuilding(target_layer_gdf)(times), 1)
            ip20 = round(CoverIndexBuilding(target_layer_gdf, ip_val = 20)(times), 1)
        feedback.pushWarning('Результирующие метрики:')
        feedback.pushWarning(f'Среднее время прибытия:     {arr_time_mean} мин.')
        feedback.pushWarning(f'Индекс прикрытия 10 мин:    {ip10} %')
        feedback.pushWarning(f'Индекс прикрытия 20 мин:    {ip20} %')
        feedback.setProgress(95)

        # Формирование итоговых слоев
        feedback.setProgressText('Формирование итоговых слоев')
        result_gdf = ox.graph_to_gdfs(G, edges=False).loc[best_nodes.keys()]
        result_gdf['name'] = pd.Series(best_nodes)

        # Перепроецируем датасет маршрутов в СК дорожной сети
        result_gdf = ox.projection.project_gdf(result_gdf, to_crs = crs_start.authid())

        # Сохраняем в итоговый слой
        result_gdf.to_file(target_file)

        # Добавляем полученный слой на карту
        vlayer = QgsVectorLayer(target_file, result_layer_name, 'ogr')
        QgsProject.instance().addMapLayer(vlayer)


        feedback.setProgress(100)
        return {self.OUTPUT: target_file}

