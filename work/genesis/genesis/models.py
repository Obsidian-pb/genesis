'''
Модели используемые в расчетах
'''

from networkx import MultiDiGraph

from genesis.tools import kmh_to_mm
from genesis.interfaces import IEnvironment

class Environment(IEnvironment):
    '''
    Модель окружения. 
    В нее входит ГДС, размещение подразделений, объектов, и т.д.
    '''
    def __init__(self, G):
        if not isinstance(G, MultiDiGraph):
            raise TypeError("Аргумент G должен быть мультиграфом!") 
        self.G = G

    def add_spatial_feature(self, spatial_feature):
        '''Добавка пространственных данных'''
        # Нужно проверить наследует ли spatial_feature интерфейсу ISpatialFeature
        pass

    def test(self):
        pass


class SpeedProfile(object):
    '''
    Модель профиля скоростей движения техники по различным типам поверхностей
    '''

    def __init__(self, precision=2):
        self._sp = {}
        self.kmh_to_mm_precision = precision
        # первоначальная инициализация
        self.set_speeds_5([40,30,25,10,5])

    def set_speeds(self, speeds:dict):
        '''
        Устанавливает скорости движения для всех типов улиц,
        переданных в соответствии с аргументом.

        Важно! Скорость указывается только в км/ч

        Аргументы
        ---------

        `speeds`:dict
            Словарь скоростей движения по различным типам улиц.
            В словаре ключ - наименование типа улицы,
            значение - скорость движения по каждому из типов улиц
        
        Пример
        ------
        sp = SP()
        sp.set_speeds_all(
            {"motorway":40,
                "trunk":35
            }
        )
        '''
        if not isinstance(speeds, dict):
            raise TypeError("Аргумент speeds должен быть только типа dict!")

        for k,v in speeds.items():
            self._sp[k]=v

    def set_speeds_5(self, speeds:list):
        '''
        Устанавливает скорости движения для всех типов улиц,
        переданных в соответствии с аргументом. При этом типы дорог разбиты
        на 5 групп.

        Важно! Скорость указывается только в км/ч

        Аргументы
        ---------
        speeds: list
            Список 5 скоростей в км/ч

            1 - наиболее крупные автомагистрали
                ["motorway", "motorway_link", "trunk", "trunk_link", "primary", 
                "primary_link", "secondary", "secondary_link"]

            2 - остальные дороги: служебные проезды:, внутриквартальные,
            въездные, парковочные
                ["road", "unclassified", "tertiary", "tertiary_link"]
            
            3 - Жилые зоны и дворовые проезды
                ["living_street", "service", "residential", "track"]

            4 - Пешеходные дорожки, тротуары и прочие пригодные
            для движения автомобилей
                ["footway", "path", "pedestrian"]

            5 - области не являющиеся дорогами, но теоретически пригодные
            для перемещения пожарной техники
                ["steps", "cycleway", "bridleway", "corridor"]

            Более подробно о типах дорог можно прочесть здесь: 
        '''
        if not isinstance(speeds, list):
            raise TypeError("Аргумент speeds должен быть только типа list!")
        if len(speeds)!=5:
            raise ValueError('Список скоростей должен состоять строго из 5 значений!')

        s_1, s_2, s_3, s_4, s_5 = speeds
        speeds_dict = {
            # Автомагистрали
            "motorway":       s_1,
            "motorway_link":  s_1,
            # Важные дороги, не являющиеся автомагистралями
            "trunk":          s_1,
            "trunk_link":     s_1,
            # Автомобильные дороги регионального значения
            "primary":        s_1,
            "primary_link":   s_1,
            # Автомобильные дороги областного значения
            "secondary":      s_1,
            "secondary_link": s_1,

            # Более важные автомобильные дороги среди прочих
            # автомобильных дорог местного значения
            "tertiary":       s_2,
            "tertiary_link":  s_2,
            # Линии, возможно, являющиеся дорогами. Временный тег,
            # которым следует помечать линии до уточнения.
            "road":           s_2,
            # Остальные автомобильные дороги местного значения,
            # образующие соединительную сеть дорог.
            "unclassified":   s_2,

            # Служебные проезды: внутриквартальные, въездные, парковочные и т.д.
            "service":        s_3,
            # Дороги, которые проходят внутри жилых зон, а также используются
            # для подъезда к ним
            "residential":    s_3,
            # Жилые зоны и дворовые проезды
            "living_street":  s_3,
            # Дороги сельскохозяйственного назначения, лесные дороги,
            # не ведущие к жилым или промышленным объектам,
            # неофициальные грунтовки, козьи тропы
            "track":          s_3,           

            # Пешеходные дорожки, тротуары.
            "footway":        s_4,           
            # Тропа (чаще всего, стихийная) использующаяся пешеходами,
            # либо одним или несколькими видами транспорта,
            # кроме четырехколесного (лыжи, снегоход, велосипед).
            "path":           s_4,
            # Для обозначения улиц городов (такого же класса как residential),
            # выделенных для пешеходов.
            "pedestrian":     s_4,

            # Лестницы, лестничные пролёты
            "steps":          s_5,
            # Велодорожка, обозначенная соответствующим дорожным знаком
            "cycleway":       s_5,
            # Дорожки для верховой езды.
            "bridleway":      s_5,
            # Коридоры внутри крупных зданий
            "corridor":       s_5,
        }
        self.set_speeds(speeds_dict)

    @property
    def sp(self):
        '''
        Текущий профиль скоростей
        '''
        return {k: kmh_to_mm(v, precision=self.kmh_to_mm_precision) for k,v in self._sp.items()}


