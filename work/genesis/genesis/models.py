'''
Модели используемые в расчетах
'''

from networkx import MultiDiGraph


class Environment(object):
    '''
    Модель окружения. 
    В нее входит ГДС, размещение подразделений, объектов, и т.д.
    '''
    def __init__(self, G):
        if not isinstance(G, MultiDiGraph):
            raise TypeError("Аргумент G должен быть мультиграфом!") 
        self.G = G