"""Выбор вычислительного режима; по умолчанию используется исходный NetworkX.

    with use_backend("scipy"):
        result = algorithm(env=G, ...)

Контекст восстанавливается после выхода, в том числе при исключении. Выбор
изолирован средствами ContextVar; новые потоки начинают с NetworkX, asyncio-задачи
наследуют контекст при создании. Это не делает кэши движка потокобезопасными.
"""

from contextlib import contextmanager
from contextvars import ContextVar
from importlib import import_module
import sys

_BACKEND = ContextVar("genesis_backend", default="networkx")


def get_backend():
    """Имя текущего режима: ``networkx`` или ``scipy``."""
    return _BACKEND.get()


def scipy_enabled():
    """Внутренняя проверка для точек подключения ускорителя."""
    return get_backend() == "scipy"


def get_engine():
    """Ленивая загрузка: обычный импорт Genesis не требует SciPy."""
    try:
        return import_module(".engine", __package__)
    except ModuleNotFoundError as exc:
        if exc.name == "scipy" or (exc.name and exc.name.startswith("scipy.")):
            raise ModuleNotFoundError(
                'Для режима scipy установите дополнительную зависимость: '
                'pip install "genesis-spatial-opt[fast]"', name="scipy"
            ) from exc
        raise


@contextmanager
def use_backend(name):
    """Включить режим только внутри блока. Вход в scipy проверяет зависимость.

    Неподдерживаемые пользовательские алгоритмы/веса/метрики продолжают
    использовать исходный путь даже внутри режима scipy.
    """
    if name not in ("networkx", "scipy"):
        raise ValueError(f"Неизвестный backend {name!r}; ожидается 'networkx' или 'scipy'")
    if name == "scipy":
        get_engine()  # Ошибка до изменения контекста и до начала расчёта.
    token = _BACKEND.set(name)
    try:
        yield
    finally:
        _BACKEND.reset(token)


def clear_cache(graph=None):
    """Сбросить уже загруженный кэш, не импортируя SciPy в обычном режиме.

    Нужен и после выхода из scipy-контекста: граф мог использоваться ранее.
    """
    engine = sys.modules.get(f"{__package__}.engine")
    if engine is not None:
        engine.clear(graph)
