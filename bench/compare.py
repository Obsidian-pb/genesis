'''
Сравнение двух прогонов сценариев: эталона и проверяемой версии.

    python bench/compare.py bench/golden/fixed.json bench/golden/new.json [--details]

Правила совпадения:
- state: те же объекты, время и ближайшее подразделение (время - до 1e-9);
- metric, deterministic: та же расстановка и то же значение метрики;
- stochastic: для каждого seed - та же расстановка (exact) или качество не хуже эталона:
  среднее и худшее значение по запускам (with_quality).
'''

import argparse
import json
import math
import statistics
from collections import defaultdict

TOL = 1e-9

# Направление метрики по имени сценария: время минимизируется, индекс прикрытия максимизируется
def _maximize(case_id):
    return '/cover' in case_id


def _close(a, b):
    if a is None or b is None:
        return a is b
    return math.isclose(a, b, rel_tol=1e-9, abs_tol=TOL)


def compare_case(case_id, ref, new):
    '''
    Возвращает (статус, пояснение). Статусы: same, quality, worse, error, ref_error
    '''
    if ref['error'] and new['error']:
        return 'same', 'ошибка в обеих версиях'
    if ref['error']:
        return 'ref_error', f'эталон: {ref["error"][:70]}'
    if new['error']:
        return 'error', new['error'][:90]
    r, n = ref['result'], new['result']
    kind = ref['kind']

    if kind == 'state':
        if r['times'].keys() != n['times'].keys():
            return 'worse', f'разные объекты: {len(r["times"])} и {len(n["times"])}'
        dt = max((abs(r['times'][k] - n['times'][k]) for k in r['times']), default=0)
        if dt > 1e-6:
            return 'worse', f'время различается до {dt:.3g}'
        diff = sum(r['nearest'][k] != n['nearest'][k] for k in r['nearest'])
        return ('same', '') if diff == 0 else ('quality', f'ближайшее различается в {diff} объектах (равноудаленные?)')

    if kind == 'metric':
        return ('same', '') if _close(r['value'], n['value']) else ('worse', f'{r["value"]} -> {n["value"]}')

    if kind == 'deterministic':
        if r['nodes'] == n['nodes'] and _close(r['value'], n['value']):
            return 'same', ''
        better = _better(case_id, n['value'], r['value'])
        return ('quality' if better else 'worse'), f'{r["value"]} -> {n["value"]}'

    if kind == 'stochastic':
        rv = [x['value'] for x in r['runs']]
        nv = [x['value'] for x in n['runs']]
        if all(a['nodes'] == b['nodes'] and _close(a['value'], b['value']) for a, b in zip(r['runs'], n['runs'])):
            return 'same', ''
        worst = max if not _maximize(case_id) else min
        ok = (_better(case_id, statistics.mean(nv), statistics.mean(rv))
              and _better(case_id, worst(nv), worst(rv)))
        note = f'среднее {statistics.mean(rv):.4g} -> {statistics.mean(nv):.4g}, худшее {worst(rv):.4g} -> {worst(nv):.4g}'
        return ('quality' if ok else 'worse'), note

    return 'worse', f'неизвестный вид {kind}'


def _better(case_id, new, ref):
    '''
    new не хуже ref с учетом направления метрики
    '''
    if new is None or ref is None:
        return False
    return new >= ref - TOL if _maximize(case_id) else new <= ref + TOL


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('reference')
    parser.add_argument('candidate')
    parser.add_argument('--details', action='store_true', help='показать каждый несовпавший сценарий')
    args = parser.parse_args()

    ref = json.load(open(args.reference, encoding='utf-8'))
    new = json.load(open(args.candidate, encoding='utf-8'))
    common = [k for k in ref['results'] if k in new['results']]

    by_status = defaultdict(list)
    by_kind = defaultdict(lambda: defaultdict(int))
    speed = []
    for case_id in common:
        r, n = ref['results'][case_id], new['results'][case_id]
        status, note = compare_case(case_id, r, n)
        by_status[status].append((case_id, note))
        by_kind[r['kind']][status] += 1
        if n['seconds'] > 0 and not r['error'] and not n['error']:
            speed.append((r['seconds'] / n['seconds'], r['seconds'], n['seconds'], case_id))

    print(f'эталон: {ref["meta"]["label"]}, проверяемая: {new["meta"]["label"]}, общих сценариев: {len(common)}')
    print('\nстатусы: same - совпадает; quality - отличается, но не хуже; worse - хуже; '
          'error - ошибка только в проверяемой; ref_error - ошибка только в эталоне')
    statuses = ['same', 'quality', 'worse', 'error', 'ref_error']
    print(f'\n{"вид":15s}' + ''.join(f'{s:>11s}' for s in statuses))
    for kind, counts in by_kind.items():
        print(f'{kind:15s}' + ''.join(f'{counts[s]:>11d}' for s in statuses))

    if speed:
        total_r = sum(s[1] for s in speed)
        total_n = sum(s[2] for s in speed)
        ratios = sorted(s[0] for s in speed)
        print(f'\nвремя всех сценариев: {total_r:.1f} с -> {total_n:.1f} с (x{total_r / total_n:.1f}); '
              f'по сценариям: медиана x{statistics.median(ratios):.1f}, от x{ratios[0]:.1f} до x{ratios[-1]:.1f}')

    show = ['worse', 'error', 'ref_error'] + (['quality'] if args.details else [])
    for status in show:
        if by_status[status]:
            print(f'\n{status}:')
            for case_id, note in by_status[status]:
                print(f'  {case_id:55s} {note}')


if __name__ == '__main__':
    main()
