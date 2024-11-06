"""
Загрузка графа улично-дорожной сети из OSM при помощи osmnx.

Сохранение напрямую в файл geopackage и загрузка слоя в проект.
"""

import networkx as nx
import osmnx as ox
import geopandas as gpd
# from shapely.geometry import Polygon, box
# from shapely.wkt import loads


from qgis.PyQt.QtCore import QCoreApplication, QVariant
from qgis.core import (
                       QgsProject,
                    #    QgsVectorLayer,
                       QgsField,
                       QgsProcessingException,
                       QgsProcessingAlgorithm,
                       QgsProcessing,
                    #    QgsProcessingParameterFileDestination,
                    #    QgsProcessingParameterExtent,
                       QgsProcessingParameterString,
                       QgsProcessingParameterMatrix,
                       QgsProcessingParameterFeatureSource,
                       QgsProcessingParameterBoolean,
                       QgsProcessingParameterDefinition,
                       QgsCoordinateReferenceSystem,
                       QgsCoordinateTransform,
                       )




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
        return 'a_gds_set_speeds'

    def displayName(self):
        """
        Отображаемое в списке имя алгоритма
        """
        return self.tr('Расчет времен следования')

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
            '''
            Расчет длин фрагментов дорожной сети, и времени следования по ним.

            В результате работы алгоритма для каждого фрагмента дорожной сети векторного слоя
            устанавливается длина фрагмента, скорость следования (в зависимости от тип дороги),
            и время следования.

            Значения устанавливаются для указанных в настройках алгоритма имен полей.
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

        # Дополнительные параметры
        params = []
        params.append(
            QgsProcessingParameterString (
                'HIGHWAY_FIELD',
                self.tr('Поле скорости следования по участку дороги'),
                defaultValue = 'highway'
            )
        )
        params.append(
            QgsProcessingParameterString (
                'LENGTH_FIELD',
                self.tr('Поле длины участка дороги'),
                defaultValue = 'length'
            )
        )
        params.append(
            QgsProcessingParameterString (
                'TRAVEL_TIME_FIELD',
                self.tr('Поле времени следования по участку дороги'),
                defaultValue = 'travel_time'
            )
        )
        params.append(
            QgsProcessingParameterString (
                'SPEED_FIELD',
                self.tr('Поле скорости следования по участку дороги'),
                defaultValue = 'maxspeed'
            )
        )
        
        for p in params:
            p.setFlags(p.flags() | QgsProcessingParameterDefinition.FlagAdvanced)
            self.addParameter(p)

        

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
        source = self.parameterAsVectorLayer(parameters, self.INPUT, context)
        ### Проверяем корректность охвата
        if source is None:
            raise QgsProcessingException(self.invalidSourceError(parameters, self.INPUT))

        ## Получение СК
        crs = self.parameterAsExtentCrs(parameters, self.INPUT, context)

        # ## Получение флага необходимости пересчета длины дорог
        # recalc_length = self.parameterAsBoolean(parameters, 'RECALC_LENGTH_FIELD', context)
       
        ## Поле типа дорог
        highway_field = self.parameterAsString(parameters, 'HIGHWAY_FIELD', context)

        ## Поле длины дороги
        length_field = self.parameterAsString(parameters, 'LENGTH_FIELD', context)

        ## Поле времени следования
        travel_time_field = self.parameterAsString(parameters, 'TRAVEL_TIME_FIELD', context)

        ## Поле скорости
        speed_field = self.parameterAsString(parameters, 'SPEED_FIELD', context)


        ## Получение скоростей следования
        speeds = self.parameterAsMatrix(parameters, 'SPEEDS', context )
        # Оставляем только скорости
        speeds = speeds[1::2]
        ### Переводим в м/мин
        s1, s2, s3, s4, s5 = [1000*float(s)/60 for s in speeds]
        ### Установка скоростей для тегов OSM
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
        # Определяем предпочтительную местную систему координат
        roads = gpd.GeoDataFrame.from_features(list(source.getFeatures())[:20], crs=crs.authid())
        estimated_crs = roads.estimate_utm_crs()

        # Если необходимо производим перепроецирование СК полигона
        transform_flag = crs.authid() != estimated_crs
        if transform_flag:
            feedback.pushInfo(f'Текущая СК ({crs.authid()}) для охвата будет приведена к локальной метрической СК {estimated_crs}')
            crs_source = crs
            crs_dest = QgsCoordinateReferenceSystem(str(estimated_crs))
            transformContext = QgsProject.instance().transformContext()  # Возможно здеь нужен слой
            tf = QgsCoordinateTransform(crs_source, crs_dest, transformContext)


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
            # Останавливаем алгоритм по нажатию Cancel
            if feedback.isCanceled():
                break

            ## Расчет длины линии
            geometry = feature.geometry()
            ## Если необходимо, перепроецируем фичу в локальную СК
            if transform_flag:
                geometry.transform(tf)
            length = geometry.length()
            feature.setAttribute(length_field, length)

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

