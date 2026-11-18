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

## Установка через uv

Из каталога `work/genesis/`:

```bash
uv pip install -e .
```

Если нужно в конкретное окружение:

```bash
# Создать окружение
uv venv .venv

# Активировать
.venv\Scripts\activate   # Windows

# Установить пакет
uv pip install -e .
```

Если нужно обновить окружение в соответствии с `pyproject.toml`, то:

```bash
pip install -e . --upgrade
```

Что это даёт:

* pip дочитает зависимости из pyproject.toml и подтянет/обновит их в текущем conda-окружении;
* -e пересоберёт ярлык на исходники (пути к genesis, graphs, fire_units, lists).



## Сборка пакета

```bash
python -m pip install -U build
python -m build
```


Тонкости:

- Команды нужно запускать из папки `work/genesis`, где лежит `pyproject.toml`.
- На выходе в `work/genesis/dist/` появятся файлы вида `genesis_spatial_opt-<версия>-py3-none-any.whl` и `.tar.gz`. В репозитории папка `dist\` уже есть — видимо, сборка запускалась ранее.
- `python -m build` изолирует окружение сборки и сам ставит себе build-зависимости (например setuptools/hatch), поэтому отдельная установка самого пакета не нужна для сборки.
- Полученный wheel затем устанавливают конечному пользователю: `pip install dist\genesis_spatial_opt-*.whl`.

То есть это именно «упаковка» библиотеки в установочный пакет, а не установка в текущее окружение разработчика (для разработки удобнее `pip install -e .`).
