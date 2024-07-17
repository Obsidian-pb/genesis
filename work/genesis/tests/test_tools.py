'''
Тесты для расчетов состояния среды

`pytest tests/test_states.py -s`
'''

import pytest

from genesis.tools import get_dict_key, k_v_dict, list_dict_concat

class TestListDictConcat:
    def test_list_dict_concat_list_list(self):
        '''
        Тест функции `list_dict_concat`:

        Склеивание двух СПИСКОВ
        '''
        a = [1,2,3]
        b = [4,5,6]

        c = list_dict_concat(a, b)
        assert c == a+b

    def test_list_dict_concat_dict_dict(self):
        '''
        Тест функции `list_dict_concat`:

        Склеивание двух СЛОВАРЕЙ
        '''
        a:dict = {1: 'a', 2: 'b'}
        b:dict = {3: 'C', 4: 'D'}

        c = list_dict_concat(a, b)
        assert c == {**a, **b}

    @pytest.mark.xfail()
    def test_list_dict_concat_list_dict(self):
        '''
        Тест функции `list_dict_concat`:

        Склеивание списка и словаря
        '''
        a:list = [1, 2, 3, 4]
        b:dict = {3: 'C', 4: 'D'}

        c = list_dict_concat(a, b)
        assert c == {**a, **b}



class TestKVDict:
    '''
    Тесты функции k_v_dict
    '''
    def test_kvd(self):
        '''
        Базовый тест.
        Ключ с наименьшим значением.
        '''
        d = {'a':10, 'b':30, 'c':20}
        cor = 'a'

        res = k_v_dict(d)

        assert cor == res

    def test_kvd_max(self):
        '''
        Базовый тест.
        Ключ с наибольшим значением.
        '''
        d = {'a':10, 'b':30, 'c':20}
        cor = 'b'

        res = k_v_dict(d, max)

        assert cor == res

class TestGetDictKey:
    '''
    Тесты функции get_dict_key
    '''
    def test_get_dict_key(self):
        '''
        Базовый тест
        '''
        d = {'a':10, 'b':30, 'c':20}
        cor = 'b'

        res = get_dict_key(d, 30)

        assert cor == res