# Вычислительные эксперименты: оценка по матрице и точное решение MCLP

Документ описывает три эксперимента на тестовом графе проекта и выводы из них для развития genesis. Он продолжает `REDESIGN_GENESIS.MD`: там предложено оценивать решения по матрице времён прибытия и решать задачи покрытия точно, здесь эти предложения проверены измерениями.

## Коротко

- Оценка расстановки по матрице на numpy даёт те же значения метрик, что и расчёт по графу, и выполняется примерно в 320 раз быстрее. Готовый класс `ArrivalTimeMatrixState` даёт только трёхкратное ускорение — его тормозит pandas.
- Матрица времён прибытия через `scipy` считается примерно в 20 раз быстрее, чем через `get_atm`, значения совпадают.
- Точный решатель находит доказанный оптимум MCLP за полсекунды.
- Генетический алгоритм с параметрами из документации ни в одном из 40 запусков не дошёл до оптимума; отставание растёт с числом подразделений — от 2 до 8 процентных пунктов.
- Жадное добавление лучше генетического алгоритма во всех случаях и быстрее его в сотни раз. От оптимума оно отстаёт на 1–2 пункта при 5 и 8 подразделениях.

## Постановка

**Данные.** Граф Сосновоборска из тестов проекта (`tests/data/test_rng.ml`), скорости по умолчанию (`DEFAULT_SPEEDS`), граф упрощён через `ox.simplify_graph`. Оставлен наибольший сильносвязный компонент: 1935 узлов, 5258 рёбер. Так каждый узел достижим из каждого, и индекс прикрытия не зависит от того, по каким узлам его считать (см. замечание Н3 в `REDESIGN_GENESIS.MD`).

**Задача.** MCLP: разместить `p` подразделений так, чтобы максимальная доля узлов была достижима за 5 минут (ИП-5, как в «Быстром старте»). Целевые объекты — все узлы графа, кандидаты на размещение — тоже все узлы. Задержка на обработку вызова (1 минута) входит во время прибытия.

**Окружение.** macOS, Python 3.12, `osmnx` 2.0.0, `networkx` 3.4.2, `pandas` 2.2.2, `numpy` 2.0.2, `scipy` 1.14.1. Код библиотеки — коммит `13df32d`, без изменений.

**Код** всех трёх экспериментов приведён в приложении.

## Эксперимент 1. Скорость оценки расстановки

**Вопрос.** Насколько быстрее оценивать расстановку по заранее посчитанной матрице, чем запускать алгоритм Дейкстры, и совпадают ли при этом значения метрик.

**Как проверялось.** 300 случайных расстановок по 5 подразделений оценивались тремя способами; для каждой считались среднее время прибытия и ИП-5.

| Способ оценки | Время одной оценки | Ускорение |
|---|---|---|
| `FirstArrivalUnitState` — алгоритм Дейкстры по графу (как сейчас) | 4,65 мс | — |
| `ArrivalTimeMatrixState` — матрица в pandas (есть в библиотеке) | 1,44 мс | в 3,2 раза |
| Матрица в numpy: минимум по выбранным столбцам | 0,014 мс | в 322 раза |

Максимальное расхождение метрик между способами — порядка 10⁻¹⁵, то есть на уровне погрешности вычислений с плавающей точкой.

Разовый расчёт самой матрицы (1935×1935, 30 МБ):

| Способ | Время |
|---|---|
| `get_atm` (на `networkx`) | 7,6 с |
| `scipy.sparse.csgraph.dijkstra` | 0,39 с |

Ускорение — в 19 раз, максимальное расхождение значений 3·10⁻¹⁴ минуты.

При повторном прогоне цифры были близкими: ускорение оценки 332 раза, расчёта матрицы — 20 раз.

**Что это значит.**

- Матричная оценка эквивалентна расчёту по графу: значения те же.
- Готовый `ArrivalTimeMatrixState` использует почти ничего из возможного выигрыша. Его время уходит на операции pandas (выбор столбцов, построение серий, словарь ближайших подразделений), а не на сам расчёт.
- Матрица окупается сразу: её расчёт через `scipy` (0,39 с) стоит как 84 оценки по графу, а метаэвристика делает их тысячи.

## Эксперимент 2. Точное решение и жадное добавление

**Вопрос.** Можно ли получить доказанный оптимум MCLP готовым решателем и насколько от него отстаёт жадное добавление.

**Как проверялось.** Задача записана как целочисленная линейная программа и решена через `scipy.optimize.milp` (решатель HiGHS):

```
max  Σ_i y_i
при  y_i ≤ Σ_{j ∈ N_i} x_j   для каждого узла i
     Σ_j x_j = p
     x_j ∈ {0, 1},  0 ≤ y_i ≤ 1
```

Здесь `x_j = 1`, если в узле `j` размещено подразделение, `y_i = 1`, если узел `i` прикрыт, `N_i` — узлы, из которых до `i` успевают за 5 минут. Жадное добавление проверялось в двух вариантах: штатный `LSCP_ADD` библиотеки и простая реализация в несколько строк; результаты совпали.

Один кандидат прикрывает в среднем 15,0 % узлов, лучший — 41,0 %.

| Подразделений | Оптимум, % | Время решателя | Жадное добавление, % | Отставание | Время `LSCP_ADD` |
|---|---|---|---|---|---|
| 2 | 51,94 | 0,64 с | 51,94 | 0 | 0,02 с |
| 3 | 58,76 | 0,57 с | 58,76 | 0 | 0,02 с |
| 5 | 71,73 | 0,48 с | 69,61 | 2,12 п. п. | 0,04 с |
| 8 | 83,36 | 0,51 с | 82,02 | 1,34 п. п. | 0,06 с |

Во всех четырёх случаях решатель подтвердил оптимальность. Для двух подразделений результат дополнительно проверен перебором всех пар узлов: те же 51,94 %.

**Что это значит.**

- Для задачи такого размера (1935 кандидатов, 1935 объектов) точное решение получается за доли секунды.
- Жадное добавление — хорошее приближение: совпадает с оптимумом при 2 и 3 подразделениях и отстаёт на 1–2 пункта при 5 и 8.
- У жадного добавления появился измеримый показатель качества. В `add_check.ipynb` точность ADD оценивается сравнением с его же результатом после отброса лишних точек; сравнение с оптимумом отвечает на тот же вопрос напрямую.

## Эксперимент 3. Генетический алгоритм против оптимума

**Вопрос.** Насколько результат генетического алгоритма библиотеки далёк от оптимума и что даёт ему перевод на матрицу.

**Как проверялось.** `BestNodesGA` с метрикой `CoverIndex(5)` и параметрами из документации: популяция 50, элита 15, 30 эпох, до 2 мутаций, селектор `RandomNodesSelector`. Для каждого числа подразделений — 10 запусков с разными `seed` и случайным стартовым размещением. Каждый запуск выполнен дважды: с `FirstArrivalUnitState` и с `ArrivalTimeMatrixState`.

| Подразделений | Оптимум, % | ГА: среднее, % | ГА: худший, % | ГА: лучший, % | Отставание среднего | Жадное добавление, % |
|---|---|---|---|---|---|---|
| 2 | 51,94 | 49,74 | 48,17 | 50,75 | 2,20 п. п. | 51,94 |
| 3 | 58,76 | 57,03 | 56,54 | 57,93 | 1,73 п. п. | 58,76 |
| 5 | 71,73 | 65,97 | 62,33 | 68,42 | 5,76 п. п. | 69,61 |
| 8 | 83,36 | 75,52 | 72,56 | 77,83 | 7,83 п. п. | 82,02 |

Время одного запуска не зависит от числа подразделений:

| Способ оценки внутри ГА | Время запуска |
|---|---|
| `FirstArrivalUnitState` (по графу) | 7,2–7,3 с |
| `ArrivalTimeMatrixState` (матрица в pandas) | 2,0 с |

Ускорение — в 3,6–3,7 раза.

**Что это значит.**

- Ни один из 40 запусков не достиг оптимума; даже лучший из десяти остаётся ниже.
- Отставание растёт с размером задачи: чем больше подразделений, тем дальше результат от оптимума.
- Генетический алгоритм проигрывает жадному добавлению во всех четырёх случаях, хотя работает в сотни раз дольше.
- Смена способа оценки на результат не влияет: во всех 40 парах запусков с одинаковым `seed` ответ совпал.
- Время генетического алгоритма почти целиком уходит на оценку решений. За запуск выполняется 1550 оценок (50 в начале и по 50 на каждой из 30 эпох); 1550 × 4,65 мс = 7,2 с — это и есть измеренное время запуска. Значит, при оценке на numpy тот же алгоритм за то же время мог бы выполнить в сотни раз больше оценок. Это расчёт по измеренным цифрам, напрямую он не проверялся.
- Известные ошибки генетического алгоритма (деление на ноль при равной приспособленности, потеря подразделений при скрещивании) в этих 40 запусках не проявились.

## Ограничения

- Один небольшой граф. На городе в десятки тысяч узлов время точного решателя может вырасти заметно, а полная матрица не поместится в память.
- Целевые объекты — узлы графа с равным весом, а не здания с весами.
- Один порог (5 минут) и одна метрика (доля прикрытых узлов).
- Генетический алгоритм запускался только с параметрами из документации. С большим числом эпох он, вероятно, подойдёт ближе к оптимуму.
- Замеры времени выполнены по одному-два раза, без статистической обработки.
- Имитация отжига не сравнивалась: для максимизируемых метрик она работает неверно (ошибка № 1 в `REDESIGN_GENESIS.MD`).

## Выводы для развития genesis

**1. Сделать матричную оценку на numpy основным способом расчёта состояния.**

Матрица хранится как массив numpy вместе с соответствием «узел → номер столбца»; оценка расстановки — минимум по выбранным столбцам. Имя первого прибывающего подразделения вычислять только по запросу: метрикам времени и прикрытия оно не нужно. Существующий `ArrivalTimeMatrixState` для этого не подходит: он даёт ускорение в 3 раза там, где возможно в 300.

**2. Считать матрицу через `scipy`.**

Замена расчёта в `get_atm` на `scipy.sparse.csgraph.dijkstra` даёт ускорение примерно в 20 раз без изменения результата. Вместе с расчётом по уникальным узлам (замечание Н6) это снимает главную претензию к матричному подходу — долгий предварительный расчёт.

**3. Добавить точный решатель как штатный алгоритм MCLP и LSCP.**

Реализация занимает около 15 строк (функция `solve_mclp` в приложении) и не требует новых зависимостей, кроме `scipy`. В рабочей версии нужны: фиксация существующих подразделений (`x_j = 1`), веса объектов, ограничение списка кандидатов и вариант для LSCP — минимум подразделений при заданном прикрытии.

**4. Жадное добавление оставить быстрым вариантом по умолчанию и дополнить шагом замены.**

Оно уже рекомендовано в документации, и эксперимент эту рекомендацию подтверждает. Отставание в 1–2 пункта можно сократить перестановками «убрать одну точку — поставить другую» после жадного этапа.

**5. Пересмотреть место метаэвристик.**

Для метрик покрытия генетический алгоритм в нынешнем виде уступает и точному решателю, и жадному добавлению — по качеству и по времени. Его область — метрики, которые не записываются линейно, и пользовательские постановки. При этом ему нужны быстрая оценка (вывод 1) и исправления из `REDESIGN_GENESIS.MD`: разнообразная стартовая популяция, турнирный отбор, скрещивание без потери подразделений.

**6. Использовать точное решение как эталон в тестах и исследованиях.**

- В тестах: проверка вида «эвристика даёт не меньше N % от оптимума на тестовом графе» вместо порогов, подобранных вручную.
- В исследованиях: сравнивать алгоритмы по отставанию от оптимума. Это заменяет полный перебор, который возможен только для одного подразделения.

**7. Дополнить документацию правилом выбора алгоритма.**

Метрика покрытия и задача умещается в память — точный решатель; нужно быстро или задача велика — жадное добавление; метрика нелинейная — метаэвристики.

## Что проверить следующим

1. **Большой город.** Время и память точного решателя на графе в десятки тысяч узлов; разреженная матрица только в пределах порога прибытия.
2. **Здания с весами** в качестве целевых объектов вместо узлов.
3. **LSCP.** Минимальное число подразделений для заданного прикрытия точным методом против результата `LSCP_ADD`.
4. **Среднее время прибытия** (задача p-медианы): точное решение на малом графе, обменный локальный поиск, генетический алгоритм.
5. **Генетический алгоритм при равном времени.** Сколько эпох нужно, чтобы догнать жадное добавление, и достижим ли оптимум при оценке на numpy.
6. **Имитация отжига** после исправления ошибки № 1.
7. **Повторные замеры времени** с усреднением.

## Приложение. Код экспериментов

Четыре файла кладутся в один каталог. Запуск — из каталога `work/genesis` репозитория, чтобы были доступны пакеты библиотеки и тестовые данные:

```
cd work/genesis
PYTHONPATH=.:<каталог со скриптами> python <каталог со скриптами>/stage1_speed.py
PYTHONPATH=.:<каталог со скриптами> python <каталог со скриптами>/stage2_exact.py
PYTHONPATH=.:<каталог со скриптами> python <каталог со скриптами>/stage3_ga.py
```

Третий скрипт работает около семи минут; число запусков задаётся переменной окружения `RUNS`.

### common.py

```python
"""Общая часть экспериментов: граф, матрица времён прибытия, точное и жадное решение MCLP."""
import time
import warnings

warnings.filterwarnings("ignore")

import networkx as nx
import numpy as np
import osmnx as ox
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import csr_matrix, eye, hstack
from scipy.sparse.csgraph import dijkstra

from fire_units.settings import DEFAULT_SPEEDS
from genesis.states import get_atm
from genesis.swiss_knife import DELAY_TIME
from graphs.speeds import kmh_to_mm, set_graph_travel_times

T_COVER = 5  # порог прикрытия, мин (ИП-5, как в «Быстром старте»)


class Timer:
    def __enter__(self):
        self.t = time.perf_counter()
        return self

    def __exit__(self, *a):
        self.dt = time.perf_counter() - self.t


def load_graph():
    """Тестовый граф с временами проезда, упрощённый; наибольший сильносвязный компонент."""
    G = ox.load_graphml("tests/data/test_rng.ml")
    set_graph_travel_times(G, DEFAULT_SPEEDS, kmh_to_mm)
    G = ox.simplify_graph(G)
    scc = max(nx.strongly_connected_components(G), key=len)
    return G.subgraph(scc).copy()


def matrix_scipy(G, weight="travel_time", delay=DELAY_TIME):
    """D[объект, кандидат] — время от кандидата до объекта с учётом задержки."""
    nodes = list(G.nodes())
    idx = {n: i for i, n in enumerate(nodes)}
    best = {}
    for u, v, d in G.edges(data=True):  # из параллельных рёбер берём самое быстрое
        key = (idx[u], idx[v])
        if key not in best or d[weight] < best[key]:
            best[key] = d[weight]
    rows, cols = zip(*best.keys())
    A = csr_matrix((list(best.values()), (rows, cols)), shape=(len(nodes), len(nodes)))
    return nodes, dijkstra(A, directed=True).T + delay


def matrix_networkx(G):
    """Та же матрица штатной функцией библиотеки (DataFrame: строки — объекты, столбцы — кандидаты)."""
    g_nodes = ox.graph_to_gdfs(G, edges=False)
    g_nodes["node"] = g_nodes.index
    return get_atm(G, g_nodes, print_calc_states=False)


def coverage(C, cols):
    """Доля объектов, прикрытых хотя бы одним из кандидатов cols, %."""
    return 100 * C[:, cols].any(axis=1).mean()


def solve_mclp(C, p, time_limit=300):
    """Точное решение MCLP: max sum(y) при y_i <= sum_{j в N_i} x_j, sum(x) = p."""
    n_obj, n_cand = C.shape
    cost = np.concatenate([np.zeros(n_cand), -np.ones(n_obj)])
    cover = LinearConstraint(hstack([-csr_matrix(C.astype(float)), eye(n_obj)], format="csr"), -np.inf, 0)
    count = LinearConstraint(csr_matrix(np.concatenate([np.ones(n_cand), np.zeros(n_obj)])[None, :]), p, p)
    integrality = np.concatenate([np.ones(n_cand), np.zeros(n_obj)])
    res = milp(cost, constraints=[cover, count], integrality=integrality, bounds=Bounds(0, 1),
               options={"time_limit": time_limit})
    return list(np.flatnonzero(res.x[:n_cand] > 0.5)), res.status == 0


def greedy_mclp(C, p):
    """Жадное добавление: каждый раз берётся кандидат, прикрывающий больше всего ещё не прикрытых объектов."""
    left, cols = np.ones(C.shape[0], dtype=bool), []
    for _ in range(p):
        j = int(np.argmax(C[left].sum(axis=0)))
        cols.append(j)
        left &= ~C[:, j]
    return cols
```

### stage1_speed.py

```python
"""Эксперимент 1. Скорость оценки расстановки: расчёт по графу против расчёта по матрице."""
import random

import numpy as np

from common import T_COVER, Timer, load_graph, matrix_networkx, matrix_scipy
from genesis.metrics import ArrivalTime, CoverIndex
from genesis.states import ArrivalTimeMatrixState, FirstArrivalUnitState

G = load_graph()
print(f"граф: {G.number_of_nodes()} узлов, {G.number_of_edges()} рёбер")

# Разовый расчёт матрицы
with Timer() as t_nx:
    M_df = matrix_networkx(G)
with Timer() as t_sp:
    nodes, D = matrix_scipy(G)
M = M_df.loc[nodes, nodes].to_numpy()
print(f"\nматрица {D.shape[0]}x{D.shape[1]}, {D.nbytes / 1e6:.0f} МБ")
print(f"  get_atm (networkx):   {t_nx.dt:6.2f} с")
print(f"  scipy.sparse.csgraph: {t_sp.dt:6.2f} с  (быстрее в {t_nx.dt / t_sp.dt:.0f} раз)")
print(f"  максимальное расхождение значений: {np.abs(M - D).max():.2e} мин")

# Оценка случайных расстановок тремя способами
random.seed(0)
P, N = 5, 300
placements = [random.sample(nodes, P) for _ in range(N)]
pos = {n: i for i, n in enumerate(nodes)}
state_graph, state_matrix = FirstArrivalUnitState(), ArrivalTimeMatrixState(M_df)
mean_metric, cover_metric = ArrivalTime(), CoverIndex(T_COVER)

res_graph, res_lib, res_np = [], [], []
with Timer() as t_graph:
    for pl in placements:
        times, _ = state_graph(env=G, points=pl)
        res_graph.append((mean_metric(times), cover_metric(times)))
with Timer() as t_lib:
    for pl in placements:
        times, _ = state_matrix(env=G, points=pl)
        res_lib.append((mean_metric(times), cover_metric(times)))
with Timer() as t_np:
    for pl in placements:
        v = D[:, [pos[n] for n in pl]].min(axis=1)
        res_np.append((v.mean(), 100 * (v <= T_COVER).mean()))

a, b, c = np.array(res_graph), np.array(res_lib), np.array(res_np)
print(f"\nоценка одной расстановки из {P} подразделений (среднее по {N} случайным):")
print(f"  FirstArrivalUnitState (Дейкстра): {1000 * t_graph.dt / N:8.3f} мс")
print(f"  ArrivalTimeMatrixState (pandas):  {1000 * t_lib.dt / N:8.3f} мс  (быстрее в {t_graph.dt / t_lib.dt:.1f} раза)")
print(f"  матрица numpy:                    {1000 * t_np.dt / N:8.3f} мс  (быстрее в {t_graph.dt / t_np.dt:.0f} раз)")
print(f"  расхождение метрик: граф/pandas {np.abs(a - b).max():.2e}, граф/numpy {np.abs(a - c).max():.2e}")
```

### stage2_exact.py

```python
"""Эксперимент 2. Точное решение MCLP и жадное добавление."""
import numpy as np

from common import T_COVER, Timer, coverage, greedy_mclp, load_graph, matrix_networkx, matrix_scipy, solve_mclp
from genesis.lscp import LSCP_ADD
from genesis.metrics import CoverIndex
from genesis.states import FirstArrivalUnitState

G = load_graph()
nodes, D = matrix_scipy(G)
C = D <= T_COVER  # C[объект, кандидат]
M_df = matrix_networkx(G)
n = len(nodes)
print(f"граф: {n} узлов | порог {T_COVER} мин | один кандидат прикрывает в среднем "
      f"{100 * C.mean():.1f} % узлов, лучший — {100 * C.mean(axis=0).max():.1f} %")

print(f"\n{'p':>2} | {'точно, %':>9} {'время, с':>9} {'оптимум':>8} | {'жадный, %':>10} | {'LSCP_ADD, %':>12} {'время, с':>9}")
exact = {}
for p in (2, 3, 5, 8):
    with Timer() as t:
        cols, proven = solve_mclp(C, p)
    exact[p] = coverage(C, cols)

    add = LSCP_ADD(state_function=FirstArrivalUnitState(), matrix=M_df, metric_function=CoverIndex(T_COVER),
                   ip_val=T_COVER, stop_case_function=lambda dynamic_nodes, **kw: len(dynamic_nodes) >= p)
    with Timer() as t_add:
        best, _ = add(env=G)
    add_cols = [nodes.index(k) for k in best]
    print(f"{p:>2} | {exact[p]:>9.2f} {t.dt:>9.2f} {'да' if proven else 'нет':>8} | "
          f"{coverage(C, greedy_mclp(C, p)):>10.2f} | {coverage(C, add_cols):>12.2f} {t_add.dt:>9.2f}")

# Проверка решателя перебором всех пар: |A ∪ B| = |A| + |B| - |A ∩ B|
Ci = C.astype(np.int32)
s = Ci.sum(axis=0)
union = s[:, None] + s[None, :] - Ci.T @ Ci
print(f"\nперебор всех пар (p=2): {100 * union.max() / n:.2f} %, решатель: {exact[2]:.2f} %")
```

### stage3_ga.py

```python
"""Эксперимент 3. Генетический алгоритм библиотеки против точного решения MCLP."""
import os
import random

import numpy as np

from common import T_COVER, Timer, coverage, load_graph, matrix_networkx, matrix_scipy, solve_mclp
from genesis.mclp import BestNodesGA
from genesis.metrics import CoverIndex
from genesis.point_selectors import RandomNodesSelector
from genesis.states import ArrivalTimeMatrixState, FirstArrivalUnitState

RUNS = int(os.environ.get("RUNS", 10))
G = load_graph()
nodes, D = matrix_scipy(G)
pos = {n: i for i, n in enumerate(nodes)}
C = D <= T_COVER
M_df = matrix_networkx(G)


def run_ga(state, p, seed):
    random.seed(seed)
    np.random.seed(seed)
    start = {node: f"псч {i}" for i, node in enumerate(random.sample(nodes, p))}
    ga = BestNodesGA(state_function=state, metric_function=CoverIndex(T_COVER), node_selector=RandomNodesSelector(),
                     population_size=50, elite_size=15, epochs=30, mutation_max_count=2)
    with Timer() as t:
        try:
            best, _ = ga(env=G, dynamic_nodes=dict(start))
        except Exception as e:
            return None, t, f"{type(e).__name__}: {e}"
    return best, t, None


print(f"ГА: популяция 50, элита 15, 30 эпох, до 2 мутаций. Запусков на каждое p: {RUNS}")
print(f"\n{'p':>2} | {'оптимум':>8} | {'ГА: среднее':>11} {'худший':>7} {'лучший':>7} {'отставание':>11} | "
      f"{'время (граф)':>12} {'(матрица)':>10} {'ускорение':>10} | замечания")
for p in (2, 3, 5, 8):
    opt = coverage(C, solve_mclp(C, p)[0])
    cov, t_graph, t_matrix, notes, same = [], [], [], [], 0
    for seed in range(RUNS):
        best, t, err = run_ga(FirstArrivalUnitState(), p, seed)
        if err:
            notes.append(f"seed {seed}: {err}")
            continue
        cov.append(coverage(C, [pos[k] for k in best]))
        t_graph.append(t.dt)
        if len(best) != p:
            notes.append(f"seed {seed}: в решении {len(best)} ПСЧ вместо {p}")
        best_m, tm, err_m = run_ga(ArrivalTimeMatrixState(M_df), p, seed)
        if not err_m:
            t_matrix.append(tm.dt)
            same += int(abs(coverage(C, [pos[k] for k in best_m]) - cov[-1]) < 1e-9)
    print(f"{p:>2} | {opt:>8.2f} | {np.mean(cov):>11.2f} {np.min(cov):>7.2f} {np.max(cov):>7.2f} "
          f"{opt - np.mean(cov):>10.2f}п | {np.mean(t_graph):>11.1f}с {np.mean(t_matrix):>9.1f}с "
          f"{np.mean(t_graph) / np.mean(t_matrix):>9.1f}x | совпало с расчётом по графу {same}/{len(t_matrix)}"
          + ("; " + "; ".join(notes) if notes else ""), flush=True)
```
