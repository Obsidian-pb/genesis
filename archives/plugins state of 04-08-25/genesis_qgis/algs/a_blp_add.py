import os
import pandas as pd
import networkx as nx
import osmnx as ox
import geopandas as gpd
from shapely.ops import unary_union

from qgis.PyQt.QtCore import QCoreApplication
from qgis.core import (
    QgsProject,
    QgsVectorLayer,
    QgsProcessingException,
    QgsProcessingAlgorithm,
    QgsProcessing,
    QgsProcessingParameterFileDestination,
    QgsProcessingParameterMatrix,
    QgsProcessingParameterString,
    QgsProcessingParameterNumber,
    QgsProcessingParameterField,
    QgsProcessingParameterEnum,
    QgsProcessingParameterFeatureSource,
    QgsProcessingParameterBoolean,
    QgsProcessingParameterDefinition,
)

from genesis_qgis.genesis_adapter import GenesisAdapter, MetricType
from genesis.metrics import ArrivalTime, CoverIndex
from genesis.states import FirstArrivalUnitState
from fire_units.metrics import ArrivalTimeBuilding, CoverIndexBuilding

class BLPAddAlgorithm(QgsProcessingAlgorithm):
    """
    Оптимальное размещение подразделения (жадное добавление)
    """
    INPUT = 'INPUT'
    EXISTED_UNITS = 'EXISTED_UNITS'
    TARGET_POINTS = 'TARGET_POINTS'
    AREA_POLYGON_LAYER = 'AREA_POLYGON_LAYER'
    SPEEDS = 'SPEEDS'
    TRAVEL_TIME_FIELD = 'TRAVEL_TIME_FIELD'
    OPTIMIZED_METRIC = 'OPTIMIZED_METRIC'
    DATA_SAMPLE_SIZE = 'DATA_SAMPLE_SIZE'
    DATA_NODE_FIELD = 'DATA_NODE_FIELD'
    WEIGHT = 'WEIGHT'
    CUTOFF = 'CUTOFF'
    DATA_CUTOFF_FIELD = 'DATA_CUTOFF_FIELD'
    TARGET_SET = 'TARGET_SET'
    IP_VAL = 'IP_VAL'
    NAMES_PATTERN = 'NAMES_PATTERN'
    START_NAMES_INDEX = 'START_NAMES_INDEX'
    NODE_FIELD = 'NODE_FIELD'
    NAME_FIELD = 'NAME_FIELD'
    RESULT_LAYER_NAME = 'RESULT_LAYER_NAME'
    SIMPLIFY = 'SIMPLIFY'
    OUTPUT = 'OUTPUT'
    PRE_GDS_PATH = '{}.ml'

    def tr(self, string):
        return QCoreApplication.translate('Processing', string)

    def createInstance(self):
        return BLPAddAlgorithm()

    def name(self):
        return 'a_blp_add'

    def displayName(self):
        return self.tr('Жадное добавление (BLP ADD)')

    def group(self):
        return self.tr('Оптимальное размещение подразделений')

    def groupId(self):
        return 'BLP_ADD'

    def shortHelpString(self):
        return self.tr('''
        Расчет оптимального размещения подразделения методом жадного добавления.
        Используется адаптер Genesis.
        ''')

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterFeatureSource(
            self.INPUT, self.tr('Слой улично-дорожной сети'), [QgsProcessing.TypeVectorLine]
        ))
        self.addParameter(QgsProcessingParameterFeatureSource(
            self.EXISTED_UNITS, self.tr('Существующие подразделения'), [QgsProcessing.TypeVectorPoint], optional=True
        ))
        self.addParameter(QgsProcessingParameterFeatureSource(
            self.TARGET_POINTS, self.tr('Целевой слой прибытия'), [QgsProcessing.TypeVectorPoint, QgsProcessing.TypeVectorPolygon], optional=True
        ))
        self.addParameter(QgsProcessingParameterFeatureSource(
            self.AREA_POLYGON_LAYER, self.tr('Границы расчетной области'), [QgsProcessing.TypeVectorPoint, QgsProcessing.TypeVectorPolygon], optional=True
        ))
        self.addParameter(QgsProcessingParameterEnum(
            self.OPTIMIZED_METRIC,
            self.tr('Целевая метрика'),
            [self.tr('Среднее время прибытия'), self.tr('ИП-10'), self.tr('ИП-20')],
            defaultValue=0
        ))
        self.addParameter(QgsProcessingParameterMatrix(
            self.SPEEDS,
            self.tr('Расчетные скорости следования'),
            numberRows=5,
            hasFixedNumberRows=True,
            headers=[self.tr('Дорога'), self.tr('Скорость')],
            defaultValue=[
                'Магистральные городские дороги и улицы общегородского значения', 49,
                'Магистральные улицы районного значения', 37,
                'Улицы и дороги местного значения', 26,
                'Служебные проезды: внутриквартальные, въездные, парковочные и т.д.', 16,
                'Пешеходные зоны и территории пригодные для передвижения пожарных автомобилей', 5
            ]
        ))
        self.addParameter(QgsProcessingParameterBoolean(self.SIMPLIFY, self.tr('Упростить граф'), True))
        # Дополнительные параметры для run_blp_add
        self.addParameter(QgsProcessingParameterNumber(self.DATA_SAMPLE_SIZE, self.tr('Размер выборки данных'), QgsProcessingParameterNumber.Integer, 100, False, 1, 10000))
        self.addParameter(QgsProcessingParameterString(self.DATA_NODE_FIELD, self.tr('Поле узла данных'), 'node'))
        self.addParameter(QgsProcessingParameterNumber(self.WEIGHT, self.tr('Вес'), QgsProcessingParameterNumber.Double, 1.0, False, 0.0, 100.0))
        self.addParameter(QgsProcessingParameterNumber(self.CUTOFF, self.tr('Порог'), QgsProcessingParameterNumber.Double, 10.0, False, 0.0, 1000.0))
        self.addParameter(QgsProcessingParameterString(self.DATA_CUTOFF_FIELD, self.tr('Поле порога данных'), 'cutoff'))
        self.addParameter(QgsProcessingParameterString(self.TARGET_SET, self.tr('Целевой набор'), ''))
        self.addParameter(QgsProcessingParameterNumber(self.IP_VAL, self.tr('Значение ИП'), QgsProcessingParameterNumber.Integer, 10, False, 1, 100))
        self.addParameter(QgsProcessingParameterString(self.NAMES_PATTERN, self.tr('Шаблон имен'), 'ПСЧ-{}'))
        self.addParameter(QgsProcessingParameterNumber(self.START_NAMES_INDEX, self.tr('Начальный индекс имен'), QgsProcessingParameterNumber.Integer, 1, False, 0, 1000))
        self.addParameter(QgsProcessingParameterString(self.NODE_FIELD, self.tr('Поле узла'), 'node'))
        self.addParameter(QgsProcessingParameterString(self.NAME_FIELD, self.tr('Поле имени'), 'name'))
        self.addParameter(QgsProcessingParameterString(self.RESULT_LAYER_NAME, self.tr('Имя итогового слоя'), 'BLP_ADD'))
        self.addParameter(QgsProcessingParameterFileDestination(
            self.OUTPUT, self.tr('Выходной файл'), 'файл Geopackage (*.gpkg)'
        ))

    def processAlgorithm(self, parameters, context, feedback):
        adapter = GenesisAdapter(feedback=feedback)
        network = self.parameterAsVectorLayer(parameters, self.INPUT, context)
        if network is None:
            raise QgsProcessingException(self.invalidSourceError(parameters, self.INPUT))
        crs = self.parameterAsExtentCrs(parameters, self.INPUT, context)
        existed_units_layer = self.parameterAsSource(parameters, self.EXISTED_UNITS, context)
        target_points_layer = self.parameterAsVectorLayer(parameters, self.TARGET_POINTS, context)
        area_layer = self.parameterAsVectorLayer(parameters, self.AREA_POLYGON_LAYER, context)
        optimized_metric = MetricType(self.parameterAsEnum(parameters, self.OPTIMIZED_METRIC, context))
        simplify = self.parameterAsBoolean(parameters, self.SIMPLIFY, context)
        speeds = self.parameterAsMatrix(parameters, self.SPEEDS, context)[1::2]
        speeds = [float(s) for s in speeds]
        result_layer_name = self.parameterAsString(parameters, self.RESULT_LAYER_NAME, context)
        target_file = self.parameterAsFile(parameters, self.OUTPUT, context)
        params = {
            'data_sample_size': self.parameterAsInt(parameters, self.DATA_SAMPLE_SIZE, context),
            'data_node_field': self.parameterAsString(parameters, self.DATA_NODE_FIELD, context),
            'weight': self.parameterAsDouble(parameters, self.WEIGHT, context),
            'cutoff': self.parameterAsDouble(parameters, self.CUTOFF, context),
            'data_cutoff_field': self.parameterAsString(parameters, self.DATA_CUTOFF_FIELD, context),
            'target_set': self.parameterAsString(parameters, self.TARGET_SET, context),
            'ip_val': self.parameterAsInt(parameters, self.IP_VAL, context),
            'names_pattern': self.parameterAsString(parameters, self.NAMES_PATTERN, context),
            'start_names_index': self.parameterAsInt(parameters, self.START_NAMES_INDEX, context),
            'node_field': self.parameterAsString(parameters, self.NODE_FIELD, context),
            'name_field': self.parameterAsString(parameters, self.NAME_FIELD, context),
        }
        roads_gdf = adapter.layer_to_gdf(network)
        G = adapter.prepare_graph(roads_gdf, speeds, simplify=simplify)
        existed_units_gdf = adapter.layer_to_gdf(existed_units_layer) if existed_units_layer else None
        target_points_gdf = adapter.layer_to_gdf(target_points_layer) if target_points_layer else None
        area_gdf = adapter.layer_to_gdf(area_layer) if area_layer else None
        estimated_utm_crs = roads_gdf.estimate_utm_crs()
        if existed_units_gdf is not None and existed_units_gdf.crs != estimated_utm_crs:
            existed_units_gdf = ox.projection.project_gdf(existed_units_gdf, to_crs=estimated_utm_crs)
        if target_points_gdf is not None and target_points_gdf.crs != estimated_utm_crs:
            target_points_gdf = ox.projection.project_gdf(target_points_gdf, to_crs=estimated_utm_crs)
        if area_gdf is not None and area_gdf.crs != estimated_utm_crs:
            area_gdf = ox.projection.project_gdf(area_gdf, to_crs=estimated_utm_crs)
        if area_gdf is not None:
            area_poly = unary_union(area_gdf.geometry)
            g_nodes_gdf = ox.graph_to_gdfs(G, edges=False)
            area = g_nodes_gdf.within(area_poly)
            nodes_list = set(g_nodes_gdf[area].index)
            if target_points_gdf is not None:
                target_points_gdf = target_points_gdf[target_points_gdf.within(area_poly)]
        else:
            area = None
            nodes_list = set(ox.graph_to_gdfs(G, edges=False).index)
        metric_func = adapter.create_metric(optimized_metric, target_points_gdf)
        best_nodes, best_metric = adapter.run_blp_add(
            G=G,
            existed_units_gdf=existed_units_gdf,
            metric_func=metric_func,
            nodes_list=nodes_list,
            params=params,
            target_gdf=target_points_gdf,
            area=area,
            feedback=feedback,
        )
        times, nearest = FirstArrivalUnitState()(env=G, points=best_nodes, area=area)
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
        result_gdf = ox.graph_to_gdfs(G, edges=False).loc[list(best_nodes.keys())]
        result_gdf['name'] = pd.Series(best_nodes)
        result_gdf = ox.projection.project_gdf(result_gdf, to_crs=crs.authid())
        result_gdf.to_file(target_file)
        vlayer = QgsVectorLayer(target_file, result_layer_name, 'ogr')
        QgsProject.instance().addMapLayer(vlayer)
        feedback.setProgress(100)
        return {self.OUTPUT: target_file} 