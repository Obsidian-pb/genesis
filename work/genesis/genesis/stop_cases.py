'''
Реализация основных класс-функций оценки достижения критерия остановки.
'''

from genesis.core import StopCaseBase


class LessEqualStopCase(StopCaseBase):
    '''
    Критерий остановки по условию "менее либо равно, чем"
    '''
    def __init__(self, value):
        self.value = value

    def __call__(self, value):
       return value <= self.value


class MoreEqualStopCase(StopCaseBase):
    '''
    Критерий остановки по условию "больше либо равно, чем"
    '''
    def  __init__(self, value):
        self.value = value

    def __call__(self, value):
        return value >= self.value

class NSameStopCase(StopCaseBase):
    '''
    Критерий остановки по условию, что на протяжении нескольких итераций
    значения равны, т.е. не изменяются
    '''
    def __init__(self, n=5):
        self.history = []
        self.n = n

    def __call__(self, value):
        self.history.append(value)
        last = self.history[-self.n:]
        return [value]*self.n == last
