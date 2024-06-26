'''
Тесты для расчетов состояния среды

`pytest tests/test_states.py -s`
'''

import pytest

from genesis.tools import list_dict_concat, kmh_to_mm

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

class TestKMHtoMM:
    def test_kmh_to_mm(self):
        '''
        Тест функции `kmh_to_mm`:

        Перевод км/ч в м/мин
        '''
        a = 30
        b = kmh_to_mm(a)
        assert b == 500

    @pytest.mark.xfail()
    def test_kmh_to_mm_str(self):
        '''
        Тест функции `kmh_to_mm`:

        Передача скорости в неверном формате
        '''
        a = '30'
        b = kmh_to_mm(a)
        assert b == 500

    def test_kmh_to_mm_prec(self):
        '''
        Тест функции `kmh_to_mm`:

        Проверка корректности округления до 2 знаков
        '''
        a = 40
        b = kmh_to_mm(a, precision=2)
        assert b == 666.67
