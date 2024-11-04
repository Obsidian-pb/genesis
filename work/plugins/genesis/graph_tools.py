'''
Дополнительные функции для работы с графами
'''

def fix_highway_list(edge):
    '''
    Функция исправления типа улицы, для случая, когда тип указан как список
    '''
    if isinstance(edge, list):
        return edge[0]
    return edge
