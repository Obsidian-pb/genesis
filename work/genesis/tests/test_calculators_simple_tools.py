'''
Тесты простых инструментальных функция модуля `calculators.py`
'''

import pytest

from genesis.tools import kmh_to_mm

def test_kmh_to_mm():
    kmh = 30
    assert kmh_to_mm(kmh)==500

@pytest.mark.xfail()
def test_kmh_to_mm_wrong_data_type():
    kmh = '30'
    assert kmh_to_mm(kmh)==500

