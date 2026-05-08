# genesis (единый дистрибутив)

Этот репозиторий содержит набор модулей:

- `genesis` — основной пакет (пространственная оптимизация)
- `graphs` — операции с графами УДС
- `fire_units` — надстройка для расчетов пожарных подразделений
- `lists` — наборы данных/справочники

## Единое пространство имён

Для удобства добавлены адаптеры, чтобы работали импорты вида:

- `from genesis.graphs.speeds import ...`
- `from genesis.fire_units.settings import ...`
- `from genesis.lists import ...`

При этом старые импорты (например, `from graphs.speeds import ...`) также остаются рабочими.

## Установка локально (для разработки)

```bash
python -m pip install -U pip
python -m pip install -e .
```

## Сборка пакета

```bash
python -m pip install -U build
python -m build
```

