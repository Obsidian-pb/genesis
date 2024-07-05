'''
Тесты для функций критерия остановки

`pytest tests/test_states.py -s`
'''

import pytest

from genesis.stop_cases import LessEqualStopCase, MoreEqualStopCase


def test_less_equal():
    '''
    Тест функции LessEqualStopCase
    '''
    less_equal = LessEqualStopCase(2)

    assert less_equal(1)
    assert not less_equal(3)
    assert less_equal(2)

def test_more_equal():
    '''
    Тест функции MoreEqualStopCase
    '''
    more_equal = MoreEqualStopCase(2)

    assert more_equal(3)
    assert not more_equal(1)
    assert more_equal(2)
