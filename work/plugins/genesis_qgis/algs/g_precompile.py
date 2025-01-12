"""
Предварительная компиляция графа дорожной сети.

Если граф был предварительно скомпилирован, все оптимизационные алгоритмы
будут использовать его, что существенно сокращает время загрузки крупных графов.

Однако, для поддержания графа в актуальном состоянии, следует выполнять данную операцию всякий раз после 
внесения изменений в слой дорожной сети на основе которого он компилируется.

Файл графа будет сохранен в папке проекта карты с именем в формате:

`{id}.ml` где `id` - уникальный идентификатор слоя дорожной сети.
"""

import networkx as nx
import osmnx as ox
import geopandas as gpd


from qgis.PyQt.QtCore import QCoreApplication
from qgis.core import (
                       QgsProject,
                       QgsVectorLayer,
                       QgsProcessingException,
                       QgsProcessingAlgorithm,
                       QgsProcessingParameterFeatureSource,
                       QgsProcessingParameterBoolean,
                       QgsProcessing,
                       )
from qgis import processing

from graphs.algorithms import graph_rise_from_gpkg




class GPrecompileAlgorithm(QgsProcessingAlgorithm):
    """
    Предварительная компиляция графа дорожной сети.
    """

    INPUT = 'INPUT'
    SIMPLIFY = 'SIMPLIFY'
    OUTPUT_PATH = '{}.ml'
    OUTPUT = 'OUTPUT'

    def tr(self, string):
        """
        Возвращает перевод для self.tr().
        """
        return QCoreApplication.translate('Processing', string)

    def createInstance(self):
        return GPrecompileAlgorithm()

    def name(self):
        """
        Название алгоритма
        """
        return 'g_precompile'

    def displayName(self):
        """
        Отображаемое в списке имя алгоритма
        """
        return self.tr('Предварительная компиляция ГДС')

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
            '''
            Предварительная компиляция графа дорожной сети.

            Если граф был предварительно скомпилирован, все оптимизационные алгоритмы
            будут использовать его, что существенно сокращает время загрузки крупных графов.

            Однако, для поддержания графа в актуальном состоянии, следует выполнять данную операцию всякий раз после 
            внесения изменений в слой дорожной сети на основе которого он компилируется.

            Файл графа будет сохранен в папке проекта карты с именем в формате:

            `{id}.ml` где `id` - уникальный идентификатор слоя дорожной сети.
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

        

    def processAlgorithm(self, parameters, context, feedback):
        """
        Код алгоритма
        """
        feedback.pushInfo('Версии библиотек:')
        feedback.pushInfo(f'   osmnx: {ox.__version__}')
        feedback.pushInfo(f'   networkx: {nx.__version__}')
        feedback.pushInfo(f'   geopandas: {gpd.__version__}')

        # =======================================================================================
        # Получение исходных параметров алгоритма
        feedback.setProgress(5)
        feedback.setProgressText('Загружаем данные')
        ## Дорожная сеть
        network             = self.parameterAsLayer(parameters, self.INPUT, context)
        if network is None:
            raise QgsProcessingException(self.invalidSourceError(parameters, self.INPUT))
        # Параметры графа дорожной сети
        simplify            = self.parameterAsBoolean(parameters, self.SIMPLIFY, context)
        # Путь к итоговому файлу
        # feedback.pushInfo(network.id())
        target_file = self.OUTPUT_PATH.format(network.id())
        


        # =======================================================================================
        # Тело алгоритма
        ## Подготавливаем геодатасеты
        feedback.setProgress(10)
        feedback.setProgressText('Подготавливаем данные')
        roads_gdf                  = gpd.GeoDataFrame.from_features(list(network.getFeatures()),
                                                                    crs=network.sourceCrs().authid())
        feedback.setProgress(30)

        # Формируем граф дорожной сети
        feedback.setProgressText('Формируем граф дорожной сети')

        ## Проверяем наличие нужных полей
        columns_list = ['highway', 'oneway', 'lanes', 'reversed']
        for col in columns_list:
            if not col in roads_gdf.columns:
                raise QgsProcessingException(f'Поле {col} отсутствует в списке полей входящего слоя дорожной сети!')
            
        ## Реконструкция графа
        G = graph_rise_from_gpkg(roads_gdf,
                                 columns_list = columns_list)
        if simplify:
            feedback.setProgress(70)
            feedback.setProgressText('Упрощаем граф дорожной сети')
            G = ox.simplify_graph(G)

        ## По умолчанию перепроецируем граф в 4326 (WGS84)
        G = ox.project_graph(G, to_latlong=True)

        ## Вывод
        g_crs = G.graph['crs']
        feedback.pushInfo(f'Получен граф дорог с количеством узлов - {G.number_of_nodes()} и ребер {G.number_of_edges()}. СК: {g_crs}')
        feedback.setProgress(90)

        # =======================================================================================
        # Сохраняем граф как файл GraphML
        ox.save_graphml(G, target_file)
        feedback.pushInfo(f'Граф сохранен по адресу: `{target_file}`')

        return {self.OUTPUT: target_file}


