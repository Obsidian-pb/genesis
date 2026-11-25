'''
Вычислительный движок: граф в виде разреженной матрицы смежности и алгоритм Дейкстры scipy.

Индекс графа (порядок узлов и матрица смежности) строится один раз на граф и кэшируется.
Кэш сбрасывается автоматически, если изменилось число узлов (проверяется при каждом вызове)
или число ребер (проверяется не чаще раза в секунду: подсчет ребер MultiDiGraph - полный обход
графа), и вручную - `clear(G)`. Функции библиотеки, меняющие веса ребер
(`graphs.speeds.set_graph_travel_times`), сбрасывают кэш сами; при изменении весов ребер
вручную нужно вызвать `clear(G)`.
'''

import time
import weakref

import networkx as nx
import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import dijkstra

_CACHE = weakref.WeakKeyDictionary()


class GraphIndex:
    '''
    Узлы графа в фиксированном порядке и матрица смежности по полю `weight`.
    Из параллельных ребер берется самое быстрое (как в networkx для MultiDiGraph).
    Ребро без поля `weight` имеет вес 1 (как в networkx).
    '''
    def __init__(self, G: nx.Graph, weight: str):
        self.weight = weight
        self.nodes = _node_array(list(G.nodes()))
        self.index = {n: i for i, n in enumerate(self.nodes.tolist())}
        self.fingerprint = _fingerprint(G)
        self.checked = time.monotonic()
        best = {}
        for u, v, d in G.edges(data=True):
            w = d.get(weight, 1)
            if isinstance(w, list):  # после упрощения графа osmnx значение может быть списком
                w = sum(w)
            key = (self.index[u], self.index[v])
            if key not in best or w < best[key]:
                best[key] = w
            if not G.is_directed():
                best[(key[1], key[0])] = best[key]
        n = len(self.nodes)
        if best:
            rows, cols = zip(*best.keys())
            # Нулевые веса хранятся явно: scipy учитывает явные элементы как ребра
            self.adjacency = csr_matrix((np.array(list(best.values()), dtype=float), (rows, cols)), shape=(n, n))
        else:
            self.adjacency = csr_matrix((n, n))
        self._nodes_int = None

    def positions(self, nodes) -> np.ndarray:
        missing = [n for n in nodes if n not in self.index]
        if missing:
            raise nx.NodeNotFound(f'Узлы {missing[:10]} отсутствуют в графе')
        return np.fromiter((self.index[n] for n in nodes), dtype=np.int64, count=len(nodes))

    def subgraph(self, positions: np.ndarray) -> 'GraphIndex':
        '''
        Индекс подграфа на узлах `positions`: пути только по ребрам между этими узлами
        '''
        sub = object.__new__(GraphIndex)
        sub.weight = self.weight
        sub.nodes = self.nodes[positions]
        sub.index = {n: i for i, n in enumerate(sub.nodes.tolist())}
        sub.fingerprint = None
        sub.checked = 0
        sub.adjacency = self.adjacency[positions][:, positions]
        sub._nodes_int = None
        return sub


def _node_array(nodes: list) -> np.ndarray:
    '''
    Одномерный массив узлов с естественным типом (int64 для числовых узлов);
    для узлов-кортежей и смешанных типов - object
    '''
    try:
        arr = np.array(nodes)
    except ValueError:
        arr = None
    if arr is None or arr.ndim != 1 or arr.dtype.kind not in 'iub':
        if arr is not None and arr.ndim == 1 and arr.dtype.kind == 'U':
            return arr.astype(object)
        arr = np.empty(len(nodes), dtype=object)
        arr[:] = nodes
    return arr


def _view_parent(G):
    '''
    Граф, подграфом-представлением которого является `G` (nx.subgraph_view с фильтром узлов
    и без фильтра ребер), или None
    '''
    parent = getattr(G, '_graph', None)
    if parent is None or not nx.is_frozen(G):
        return None
    if getattr(G, '_EDGE_OK', None) is not nx.filters.no_filter:
        return None
    return parent


def _fingerprint(G):
    return (G.number_of_nodes(), G.number_of_edges())


def graph_index(G: nx.Graph, weight: str = 'travel_time') -> GraphIndex:
    '''
    Индекс графа из кэша или построенный заново
    '''
    try:
        per_graph = _CACHE.setdefault(G, {})
    except TypeError:  # объект не поддерживает weakref - без кэша
        return GraphIndex(G, weight)
    index = per_graph.get(weight)

    # Подграф-представление (G.subgraph(...)) кэшированного графа: срез матрицы родителя
    # вместо построения индекса по ребрам подграфа
    parent = _view_parent(G)
    if parent is not None:
        if index is None:
            parent_index = graph_index(parent, weight)
            index = parent_index.subgraph(parent_index.positions(list(G.nodes())))
            per_graph[weight] = index
        return index
    if index is not None and index.fingerprint[0] == G.number_of_nodes():
        now = time.monotonic()
        if now - index.checked < EDGES_CHECK_SECONDS:
            return index
        if index.fingerprint == _fingerprint(G):
            index.checked = now
            return index
    index = GraphIndex(G, weight)
    per_graph[weight] = index
    return index


# Как часто перепроверять число ребер графа из кэша, с
EDGES_CHECK_SECONDS = 1.0


def clear(G: nx.Graph = None):
    '''
    Сбросить кэш индекса графа `G` (или всех графов)
    '''
    if G is None:
        _CACHE.clear()
    else:
        _CACHE.pop(G, None)


def first_arrival(index: GraphIndex, sources: np.ndarray, delay: float = 0, cutoff: float = None):
    '''
    Время прибытия первого подразделения в каждый узел графа.

    Аргументы
    ---------
    `index`: GraphIndex
    `sources`: np.ndarray
        Позиции узлов подразделений в `index.nodes`.
    `delay`: float
        Задержка, добавляется ко времени.
    `cutoff`: float = None
        Ограничение длины пути (без задержки), как `cutoff` в networkx.

    Возвращает
    ----------
    `reached`: np.ndarray - позиции достижимых узлов,
    `times`: np.ndarray - время прибытия с задержкой,
    `source`: np.ndarray - номер подразделения (позиция в `sources`) для каждого достижимого узла.
    '''
    limit = np.inf if cutoff is None else cutoff
    dist, _, src = dijkstra(index.adjacency, directed=True, indices=sources, min_only=True,
                            return_predecessors=True, limit=limit)
    reached = np.flatnonzero(np.isfinite(dist))
    # Номер источника: позиция узла-источника -> порядковый номер подразделения
    order = np.empty(len(index.nodes), dtype=np.int64)
    order[sources] = np.arange(len(sources))
    return reached, dist[reached] + delay, order[src[reached]]


# ---------------------------------------------------------------------------
# Нативная оценка расстановки: строки расстояний из кэша и метрика на numpy

# Предел памяти под кэш строк расстояний одного графа, байт
ROWS_CACHE_BYTES = 1 << 30


def distance_rows(index: GraphIndex, positions: np.ndarray) -> np.ndarray:
    '''
    Расстояния от узлов `positions` до всех узлов графа (строки k x n, без задержки).
    Недостающие строки считаются одним вызовом алгоритма Дейкстры и кэшируются в индексе
    '''
    cache = index.__dict__.setdefault('_rows', {})
    missing = [p for p in dict.fromkeys(positions.tolist()) if p not in cache]
    if missing:
        n = len(index.nodes)
        if (len(cache) + len(missing)) * n * 8 > ROWS_CACHE_BYTES:
            cache.clear()
        dist = dijkstra(index.adjacency, directed=True, indices=missing)
        for p, row in zip(missing, np.atleast_2d(dist)):
            cache[p] = row
    return np.stack([cache[p] for p in positions.tolist()])


def area_mask(index: GraphIndex, area) -> np.ndarray:
    '''
    Маска `area` (pd.Series, индекс - узлы) в порядке узлов индекса; узлы вне `area` - False
    '''
    cache = index.__dict__.setdefault('_areas', {})
    hit = cache.get(id(area))
    if hit is not None and hit[0] is area:
        return hit[1]
    mask = area.reindex(index.nodes).fillna(False).to_numpy(dtype=bool)
    if len(cache) > 32:
        cache.clear()
    cache[id(area)] = (area, mask)
    return mask


def _native_state(state):
    '''
    Состояние, которое можно считать по строкам расстояний: FirstArrivalUnitState
    со стандартным алгоритмом и весом-именем поля
    '''
    from .states import FirstArrivalUnitState
    from .swiss_knife import MSF
    if type(state) is not FirstArrivalUnitState:
        return False
    return state.state_algorithm is MSF and isinstance(state.weight, str)


def evaluate(state, metric, env, nodes, area=None, **kwargs):
    '''
    Значение метрики расстановки `nodes` и число учтенных узлов - как
    `metric(state(env, nodes, area)[0])` и `len(...)`, но без pandas и без алгоритма Дейкстры
    на уже рассчитанных узлах.

    Возвращает None, если состояние или метрика не поддерживают нативный расчет:
    тогда вызывающий код считает прежним способом.
    '''
    if kwargs or not _native_state(state):
        return None
    # Не обходить __call__ пользовательского подкласса унаследованным _native.
    native = getattr(metric, '_native', None) if '_native' in type(metric).__dict__ else None
    if native is None:
        return None
    index = graph_index(env, state.weight)
    rows = distance_rows(index, index.positions(list(nodes)))
    times = rows[0] if len(rows) == 1 else rows.min(axis=0)
    selected = np.isfinite(times)
    if area is not None:
        selected &= area_mask(index, area)
    positions = np.flatnonzero(selected)
    value = native(times[positions] + state.delay, positions, index)
    if value is NotImplemented:
        return None
    return len(positions), value


def node_weights(owner, index: GraphIndex, frame, node_field: str, value_field: str = None) -> np.ndarray:
    '''
    Вес каждого узла индекса: число записей `frame` (зданий) на узле или сумма `value_field`.
    Кэшируется в объекте `owner` (метрике) для каждого индекса
    '''
    cache = owner.__dict__.setdefault('_native_weights', {})
    key = (id(index), value_field)
    hit = cache.get(key)
    if hit is not None and hit[0] is index:
        return hit[1]
    grouped = frame.groupby(node_field).size() if value_field is None else frame.groupby(node_field)[value_field].sum()
    weights = np.zeros(len(index.nodes))
    for node, value in grouped.items():
        pos = index.index.get(node)
        if pos is not None:
            weights[pos] = value
    if len(cache) > 32:
        cache.clear()
    cache[key] = (index, weights)
    return weights



def arrival_distances(index: GraphIndex, positions: np.ndarray, limits: np.ndarray = None, targets=None,
                      batch_size: int = 256) -> csr_matrix:
    '''
    Расстояния ДО узлов `positions` (строки) от узлов графа (столбцы в порядке индекса) - разреженная
    матрица: хранятся только достигнутые пары (явно, в том числе нулевые расстояния).
    `limits` - ограничение расстояния для каждой строки (включительно); `targets` - допустимые
    узлы-столбцы. Плотный массив существует только для одного пакета строк
    '''
    reverse = index.__dict__.get('_reverse')
    if reverse is None:
        reverse = index.adjacency.T.tocsr()
        index._reverse = reverse
    n = len(index.nodes)
    allowed = None
    if targets is not None:
        allowed = np.zeros(n, dtype=bool)
        allowed[[index.index[t] for t in targets if t in index.index]] = True
    data, indices, pointers = [], [], [np.zeros(1, dtype=np.int64)]
    offset = 0
    for start in range(0, len(positions), batch_size):
        chunk = positions[start:start + batch_size]
        chunk_limits = None if limits is None else limits[start:start + batch_size]
        limit = np.inf if chunk_limits is None else float(np.nanmax(chunk_limits))
        dist = np.atleast_2d(dijkstra(reverse, directed=True, indices=chunk, limit=limit))
        keep = np.isfinite(dist)
        if chunk_limits is not None:
            keep &= dist <= chunk_limits[:, None]
        if allowed is not None:
            keep &= allowed[None, :]
        rows, cols = np.nonzero(keep)          # строки по возрастанию: подряд для каждой строки
        data.append(dist[rows, cols])
        indices.append(cols.astype(np.int32))
        pointers.append(offset + np.cumsum(np.bincount(rows, minlength=len(chunk))))
        offset = int(pointers[-1][-1]) if len(chunk) else offset
    data = np.concatenate(data) if data else np.empty(0)
    indices = np.concatenate(indices) if indices else np.empty(0, dtype=np.int32)
    indptr = np.concatenate(pointers)
    return csr_matrix((data, indices, indptr), shape=(len(positions), n))


def first_appearance(dist: csr_matrix) -> np.ndarray:
    '''
    Столбцы в порядке первого появления: строка за строкой, внутри строки - по возрастанию
    расстояния (так складываются столбцы при сборке DataFrame из результатов networkx)
    '''
    seen = np.zeros(dist.shape[1], dtype=bool)
    order = []
    for i in range(dist.shape[0]):
        cols = dist.indices[dist.indptr[i]:dist.indptr[i + 1]]
        vals = dist.data[dist.indptr[i]:dist.indptr[i + 1]]
        new = ~seen[cols]
        if new.any():
            cols, vals = cols[new], vals[new]
            cols = cols[np.argsort(vals, kind='stable')]
            order.extend(cols.tolist())
            seen[cols] = True
            if seen.all():
                break
    return np.array(order, dtype=np.int64)


def atm_layout(dist: csr_matrix, batch_size: int):
    '''
    Порядок строк и столбцов матрицы прибытия, как у сборки `get_atm` через
    `pd.DataFrame.from_dict(..., orient='index')` пакетами по `batch_size` и `pd.concat`:
    - столбцы - в порядке первого появления по всем строкам;
    - строки внутри пакета упорядочиваются по первому (в порядке столбцов пакета) столбцу,
      в котором у строки есть значение; строки без значений выпадают.
    Возвращает (номера строк, номера столбцов)
    '''
    columns = first_appearance(dist)
    rows = []
    for start in range(0, dist.shape[0], batch_size):
        batch = dist[start:start + batch_size]
        rank = np.full(dist.shape[1], np.inf)
        batch_columns = first_appearance(batch)
        rank[batch_columns] = np.arange(len(batch_columns))
        key = np.full(batch.shape[0], np.inf)
        counts = np.diff(batch.indptr)
        present = np.flatnonzero(counts)
        if len(present):
            key[present] = np.minimum.reduceat(rank[batch.indices], batch.indptr[:-1][present])
        present = np.flatnonzero(np.isfinite(key))
        rows.extend((start + present[np.argsort(key[present], kind='stable')]).tolist())
    return np.array(rows, dtype=np.int64), columns


def fill_dense(dist: csr_matrix, rows: np.ndarray, columns: np.ndarray, delay: float) -> np.ndarray:
    '''
    Плотная матрица (rows x columns) из разреженной: NaN - не достигнут; к значениям добавляется `delay`.
    Строится один раз, без промежуточных полных копий
    '''
    out = np.full((len(rows), len(columns)), np.nan)
    position = np.full(dist.shape[1], -1, dtype=np.int64)
    position[columns] = np.arange(len(columns))
    for i, r in enumerate(rows):
        cols = dist.indices[dist.indptr[r]:dist.indptr[r + 1]]
        vals = dist.data[dist.indptr[r]:dist.indptr[r + 1]]
        pos = position[cols]
        ok = pos >= 0
        out[i, pos[ok]] = vals[ok] + delay
    return out


def cached(G: nx.Graph, key: str, build):
    '''
    Производные данные графа (например, спроецированные координаты узлов), построенные
    `build(G)` один раз. Сбрасываются вместе с кэшем графа и при изменении числа узлов
    '''
    try:
        per_graph = _CACHE.setdefault(G, {})
    except TypeError:
        return build(G)
    hit = per_graph.get(('cached', key))
    if hit is not None and hit[0] == G.number_of_nodes():
        return hit[1]
    value = build(G)
    per_graph[('cached', key)] = (G.number_of_nodes(), value)
    return value


def projected_nodes(G: nx.Graph):
    '''
    GeoDataFrame узлов в метрической системе координат (как ox.graph_to_gdfs + project_gdf)
    '''
    import osmnx as ox

    def build(G):
        g_nodes = ox.graph_to_gdfs(G, edges=False)
        if not ox.projection.is_projected(g_nodes.crs):
            g_nodes = ox.projection.project_gdf(g_nodes)
        return g_nodes
    return cached(G, 'projected_nodes', build)


def projected_graph(G: nx.Graph):
    '''
    Граф в метрической системе координат (ox.project_graph)
    '''
    import osmnx as ox
    return cached(G, 'projected_graph', ox.project_graph)


def shortest_path(index: GraphIndex, source: int, target: int):
    '''
    Узлы кратчайшего пути от позиции `source` до позиции `target` или None, если пути нет
    '''
    dist, pred = dijkstra(index.adjacency, directed=True, indices=source, return_predecessors=True)
    if not np.isfinite(dist[target]):
        return None
    path = [target]
    while path[-1] != source:
        path.append(pred[path[-1]])
    return index.nodes[path[::-1]].tolist()
