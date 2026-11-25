'''
Прогон сценариев на установленной версии genesis и сохранение результатов в JSON.

    python bench/run.py --label fixed --out bench/golden/fixed.json [--only grid]

Запускается из корня репозитория. Какая версия genesis используется, определяется
окружением Python, в котором запущен скрипт.
'''

import argparse
from contextlib import nullcontext
import json
import platform
import sys
import time
import traceback
import warnings

warnings.filterwarnings('ignore')

sys.path.insert(0, 'bench')
import scenarios  # noqa: E402


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--label', required=True)
    parser.add_argument('--out', required=True)
    parser.add_argument('--only', default=None, help='подстрока id сценариев')
    parser.add_argument('--backend', choices=('networkx', 'scipy'), default=None,
                        help='явный режим; без аргумента — штатный режим версии (включая старую базу)')
    args = parser.parse_args()

    context = nullcontext()
    if args.backend is not None:
        from genesis.backends import use_backend
        context = use_backend(args.backend)
    with context:
        run(args)


def run(args):
    import genesis
    graphs = scenarios.load_graphs()
    cases = [c for c in scenarios.build(graphs) if args.only is None or args.only in c[0]]

    results = {}
    started = time.perf_counter()
    for i, (case_id, kind, func) in enumerate(cases, 1):
        t = time.perf_counter()
        try:
            res, error = func(), None
        except Exception as e:  # ошибки эталона тоже результат
            res, error = None, f'{type(e).__name__}: {e}'
            traceback.print_exc(limit=1)
        dt = time.perf_counter() - t
        results[case_id] = {'kind': kind, 'result': res, 'error': error, 'seconds': dt}
        print(f'[{i}/{len(cases)}] {case_id:55s} {dt:7.2f} s{"  ОШИБКА " + error[:60] if error else ""}', flush=True)

    meta = {'label': args.label, 'backend': args.backend or 'default',
            'genesis_file': genesis.__file__, 'python': platform.python_version(),
            'total_seconds': time.perf_counter() - started}
    with open(args.out, 'w', encoding='utf-8') as f:
        json.dump({'meta': meta, 'results': results}, f, ensure_ascii=False, indent=1)
    print(f'сохранено: {args.out}, сценариев {len(results)}, {meta["total_seconds"]:.0f} с')


if __name__ == '__main__':
    main()
