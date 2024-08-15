'''
Утилиты разработки
'''

import time


def timing(f, msg='', acc=2, return_time=False):
    '''
    Обертка счетчика затраченного времени
    '''
    def _timing(**kwargs):
        # Фиксация стартового времени функции
        st = time.time()

        # Собственно оборачиваемая функция
        r = f(**kwargs)

        # Печать времени работы функции
        ft = time.time()
        td = round(ft-st,acc)
        if msg == '':
            print(f'ВРЕМЯ: {td} сек')
        else:
            print(f'{msg} {td} сек')
        if return_time:
            return *r, td
        return r
    
    return _timing


class Progressbar(object):
    '''
    Прогресс бар для использования в итеративных функциях
    '''
    def __init__(self, maxval, minval=0, bins=10, ok_char='#', est_char='_'):
        self.maxval = maxval
        self.minval = minval
        self.bins = bins
        self.scope = maxval-minval
        self.val=minval
        self.ok_char = ok_char
        self.est_char = est_char

    def __call__(self, **kwargs):
        self.val+=1
        bins_ok = int(self.bins*(self.val/self.scope))
        bins_still = self.bins-bins_ok
        s = "|"+self.ok_char*bins_ok + self.est_char*bins_still + "| " + f'{round(100*self.val/self.scope, 1)}%'
        print(s, end='\r')
        if bins_ok==self.bins:
            print('')


class TimeCheckPoint(object):
    '''
    Таймер

    `acc`:int
        Точность округления
    '''
    def __init__(self, acc:int=2):
        self.acc = acc
        self.prev = time.time()
    
    def __call__(self, switch=True):
        now = time.time()
        diff = round(now - self.prev, self.acc)
        if switch:
            self.prev = now
        return diff