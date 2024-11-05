"""
Загрузка графа улично-дорожной сети из OSM при помощи osmnx.

Сохранение напрямую в файл geopackage и загрузка слоя в проект.
"""

import networkx as nx
import osmnx as ox
import geopandas as gpd
from shapely.geometry import Polygon, box
from shapely.wkt import loads


from qgis.PyQt.QtCore import QCoreApplication, QVariant
from qgis.core import (
                       QgsProject,
                       QgsVectorLayer,
                       QgsField,
                       QgsProcessingException,
                       QgsProcessingAlgorithm,
                       QgsProcessing,
                       QgsProcessingParameterFileDestination,
                       QgsProcessingParameterExtent,
                       QgsProcessingParameterString,
                       QgsProcessingParameterMatrix,
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
                self.tr('Слой улично-дорожной сети'),
                [QgsProcessing.TypeVectorLine]
            )
        )

        # Пересчитать длину дорог
        self.addParameter(
            QgsProcessingParameterBoolean (
                'RECALC_LENGTH',
                self.tr('Пересчитать длину дорог'),
                False
            )
        )


        # Расчетные скорости следования
        self.addParameter(
            QgsProcessingParameterMatrix (
                'SPEEDS',
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


        

    def processAlgorithm(self, parameters, context, feedback):
        """
        Код алгоритма
        """
        length_field = 'length'
        # Название поля в котором будет сохранено время следования
        travel_time_field = 'travel_time'
        # Название поля в котором будет сохранено значение скорости следования
        speed_field = 'maxspeed'

        highway_field = 'highway'


        feedback.pushInfo('Версии библиотек:')
        feedback.pushInfo(f'   osmnx: {ox.__version__}')
        feedback.pushInfo(f'   networkx: {nx.__version__}')
        feedback.pushInfo(f'   geopandas: {gpd.__version__}')

        # Получение исходных параметров алгоритма
        ## Загрузка охвата
        source = self.parameterAsVectorLayer(
            parameters,
            self.INPUT,
            context
        )
        ### Проверяем корректность охвата
        if source is None:
            raise QgsProcessingException(self.invalidSourceError(parameters, self.INPUT))

        ## Получение СК
        crs = self.parameterAsExtentCrs(
            parameters,
            self.INPUT,
            context
        )
        ### Проверяем корректность охвата
        if crs is None:
            raise QgsProcessingException(self.invalidSourceError(parameters, self.INPUT))


        ## Получение флага необходимости пересчета длины дорог
        recalc_length = self.parameterAsBoolean(
            parameters,
            'RECALC_LENGTH',
            context
        )
        if recalc_length is None:
            raise QgsProcessingException(self.invalidSourceError(parameters, self.INPUT))        

        ## Получение скоростей следования
        speeds = self.parameterAsMatrix(
            parameters,
            'SPEEDS',
            context
        )
        if speeds is None:
            raise QgsProcessingException(self.invalidSourceError(parameters, self.INPUT))
        speeds = speeds[1::2]
        ### Переводим в м/мин
        s1, s2, s3, s4, s5 = [1000*s/60 for s in speeds]

        # 2 Установка скоростей для тегов OSM
        sp = {
                "trunk":          s1,           # Важные дороги, не являющиеся автомагистралями
                "trunk_link":     s1,           # Важные дороги, не являющиеся автомагистралями
                "motorway":       s1,           # Автомагистрали 
                "motorway_link":  s1,           # Автомагистрали 

                "primary":        s2,           # Автомобильные дороги регионального значения
                "primary_link":   s2,           # Автомобильные дороги регионального значения
                "secondary":      s2,           # Автомобильные дороги областного значения
                "secondary_link": s2,           # Автомобильные дороги областного значения
                "unclassified":   s2,           # Остальные автомобильные дороги местного значения, образующие соединительную сеть дорог.

                "tertiary":       s3,           # Более важные автомобильные дороги среди прочих автомобильных дорог местного значения
                "tertiary_link":  s3,           # Более важные автомобильные дороги среди прочих автомобильных дорог местного значения
                "residential":    s3,           # Дороги, которые проходят внутри жилых зон, а также используются для подъезда к ним
                "living_street":  s3,           # Жилые зоны и дворовые проезды

                "road":           s4,           # Линии, возможно, являющиеся дорогами. Временный тег, которым следует помечать линии до уточнения.
                "service":        s4,           # Служебные проезды: внутриквартальные, въездные, парковочные и т.д.
                "track":          s4,           # Дороги сельскохозяйственного назначения, лесные дороги, не ведущие к жилым или промышленным объектам, неофициальные грунтовки, козьи тропы

                "footway":        s5,           # Пешеходные дорожки, тротуары. 
                "path":           s5,           # Тропа (чаще всего, стихийная) использующаяся пешеходами, либо одним или несколькими видами транспорта, кроме четырехколесного (лыжи, снегоход, велосипед).
                "pedestrian":     s5,           # Для обозначения улиц городов (такого же класса как residential), выделенных для пешеходов.

                "steps":          s5,           # Лестницы, лестничные пролёты. 
                "cycleway":       s5,           # Велодорожка, обозначенная соответствующим дорожным знаком. 
                "bridleway":      s5,           # Дорожки для верховой езды.
                "corridor":       s5,           # Коридоры внутри крупных зданий
            }
       

        # Тело алгоритма
        # Если необходимо производим перепроецирование СК полигона
        # if crs.authid() != 'EPSG:4326':
        #     feedback.pushInfo(f'Текущая СК ({crs.authid()}) для охвата будет приведена к СК WGS 84 [EPSG: 4326]')
        #     crs_source = crs
        #     crs_dest = QgsCoordinateReferenceSystem("EPSG:4326")
        #     transformContext = QgsProject.instance().transformContext()
        #     xform = QgsCoordinateTransform(crs_source, crs_dest, transformContext)
        #     source  = xform.transform(source)



        # Активируем возможность редактирования слоя
        source.beginEditCommand("Расчет времен следования")
        source.startEditing()
        
        # Проверяем, имеется ли поле travel_time_field в списке полей
        if not travel_time_field in source.attributeList ():
            source.addAttribute(
                QgsField(name = travel_time_field,
                    type = QVariant.Double,
                    typeName = 'Real')
            )
        # Проверяем, имеется ли поле speed_field в списке полей
        if not speed_field in source.attributeList ():
            source.addAttribute(
                QgsField(name = speed_field,
                    type = QVariant.Double,
                    typeName = 'Real')
            )
        # Проверяем, имеется ли поле length_field в списке полей
        if not length_field in source.attributeList ():
            source.addAttribute(
                QgsField(name = length_field,
                    type = QVariant.Double,
                    typeName = 'Real')
            )        



        # Перебираем все фичи слоя:
        features = source.getFeatures()

        total = 100 / source.featureCount()
        for current, feature in enumerate(features):
            # Stop the algorithm if cancel button has been clicked
            if feedback.isCanceled():
                break

            ## Расчет длины линии
            if recalc_length:
                geometry = feature.geometry()
                length = geometry.length()
                feature.setAttribute(length_field, length)
            else:
                length = feature.attribute(length_field)

            ## Определение скорости
            road = feature.attribute(highway_field)
            speed = sp.get(road, s5)
 
            ## Вносим изменения в фичи
            feature.setAttribute(speed_field, speed)
            feature.setAttribute(travel_time_field, length/speed)
            source.updateFeature(feature)

            # Обновление прогрессбара
            feedback.setProgress( int(current * total) )



        # Сохраняем изменения в слое и закрываем редактирование
        source.commitChanges()
        source.endEditCommand()


        


        # dest_id = '0'
        return {self.OUTPUT: 'Ok'}

