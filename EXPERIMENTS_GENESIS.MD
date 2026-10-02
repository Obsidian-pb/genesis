# Вычислительные эксперименты: оценка по матрице и точное решение MCLP

Документ описывает четыре эксперимента и выводы из них для развития genesis: три на тестовом графе проекта (Сосновоборск) и один на графе Красноярска. Он продолжает `REDESIGN_GENESIS.MD`: там предложено оценивать решения по матрице времён прибытия и решать задачи покрытия точно, здесь эти предложения проверены измерениями.

## Коротко

- Оценка расстановки по матрице на numpy даёт те же значения метрик, что и расчёт по графу, и выполняется примерно в 320 раз быстрее. Готовый класс `ArrivalTimeMatrixState` даёт только трёхкратное ускорение — его тормозит pandas.
- Матрица времён прибытия через `scipy` считается примерно в 20 раз быстрее, чем через `get_atm`, значения совпадают.
- Точный решатель находит доказанный оптимум MCLP за полсекунды.
- Генетический алгоритм с параметрами из документации ни в одном из 40 запусков не дошёл до оптимума; отставание растёт с числом подразделений — от 2 до 8 процентных пунктов.
- Жадное добавление лучше генетического алгоритма во всех случаях и быстрее его в сотни раз. От оптимума оно отстаёт на 1–2 пункта при 5 и 8 подразделениях.
- На Красноярске (68 815 зданий, 32 082 кандидата) точный решатель «в лоб» за 10 минут не справляется: предел для него — между 26 и 44 миллионами пар «объект — кандидат».
- Если сократить список кандидатов до 5 000, оптимум для всего города находится за 28 секунд и оказывается на 1,4 пункта выше, чем результат жадного добавления на полном списке.

## Постановка

Этот раздел относится к экспериментам 1–3; постановка эксперимента 4 описана в нём самом.

**Данные.** Граф Сосновоборска из тестов проекта (`tests/data/test_rng.ml`), скорости по умолчанию (`DEFAULT_SPEEDS`), граф упрощён через `ox.simplify_graph`. Оставлен наибольший сильносвязный компонент: 1935 узлов, 5258 рёбер. Так каждый узел достижим из каждого, и индекс прикрытия не зависит от того, по каким узлам его считать (см. замечание Н3 в `REDESIGN_GENESIS.MD`).

**Задача.** MCLP: разместить `p` подразделений так, чтобы максимальная доля узлов была достижима за 5 минут (ИП-5, как в «Быстром старте»). Целевые объекты — все узлы графа, кандидаты на размещение — тоже все узлы. Задержка на обработку вызова (1 минута) входит во время прибытия.

**Окружение.** macOS, Python 3.12, `osmnx` 2.0.0, `networkx` 3.4.2, `pandas` 2.2.2, `numpy` 2.0.2, `scipy` 1.14.1. Код библиотеки — коммит `13df32d`, без изменений.

**Код** всех экспериментов приведён в приложениях.

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

## Эксперимент 4. Точный решатель на большом городе

**Вопрос.** До какого размера задачи точный решатель остаётся практичным и что делать, когда он перестаёт справляться.

**Данные.** Красноярск из OpenStreetMap, загрузка по схеме из `docs/pages/210_data_preparation.ipynb`: границы города, дорожная сеть типа `drive_service` с буфером 1000 м, здания в границах города.

| | Количество |
|---|---|
| Узлов дорожной сети в исходном графе | 98 074 |
| Узлов после упрощения графа | 34 141 |
| Узлов в наибольшем сильносвязном компоненте | 34 041 (84 046 рёбер) |
| Кандидатов на размещение — узлы в границах города | 32 082 |
| Зданий | 68 815 |
| Объектов — узлы, к которым привязаны здания | 19 519 |
| Пар «объект — кандидат» в пределах порога | 71,1 млн (плотность 11,3 %) |

Здания привязаны к ближайшему узлу (медиана расстояния 43 м; дальше 300 м — 0,4 % зданий) и сгруппированы по узлам: объект — это узел с весом, равным числу зданий. Результат от группировки не меняется, а число строк задачи сокращается в 3,5 раза.

**Задача.** MCLP с весами: разместить `p` подразделений так, чтобы за 10 минут (ИП-10, задержка 1 минута входит) было достижимо максимальное число зданий:

```
max  Σ_i w_i · y_i
при  y_i ≤ Σ_{j ∈ N_i} x_j   для каждого объекта i
     Σ_j x_j = p
```

**Как проверялось.** Матрица покрытия строилась через `scipy.sparse.csgraph.dijkstra` с ограничением по времени и хранилась в разреженном виде. Задачи меньшего размера получались случайной выборкой объектов и кандидатов. Каждая задача решалась в отдельном процессе с лимитом решателя 600 секунд; для сравнения на той же задаче выполнялось жадное добавление с весами. Память — пиковая для процесса, включая около 0,5 ГБ на загрузку полной матрицы.

Матрица покрытия для всего города построена за 13 секунд. Для ориентира: в `atm_transpose_avoid.ipynb` расчёт матрицы для Красноярска через `get_atm` занял 1 час 36 минут. Постановки не идентичны (там граф не упрощён, а расчёт ведётся по каждому из 58 094 зданий), поэтому это не прямое сравнение.

### Рост размера задачи

10 подразделений.

| Объектов × кандидатов | Пар, млн | Время решателя | Память | Точный решатель | Жадное добавление |
|---|---|---|---|---|---|
| 2 000 × 2 000 | 0,5 | 0,4 с | 0,6 ГБ | 91,28 % — оптимум | 89,24 % |
| 5 000 × 5 000 | 2,8 | 4,3 с | 1,4 ГБ | 91,48 % — оптимум | 90,13 % |
| 10 000 × 10 000 | 11,4 | 19 с | 3,9 ГБ | 91,70 % — оптимум | 88,77 % |
| 15 000 × 15 000 | 25,6 | 354 с | 13,4 ГБ | 91,66 % — оптимум | 90,35 % |
| 19 519 × 20 000 | 44,4 | лимит | 13,7 ГБ | 28,71 % — не решено | 90,06 % |
| 19 519 × 32 082 (весь город) | 71,1 | лимит | 13,8 ГБ | 21,60 % — не решено | 90,19 % |

Жадное добавление отработало за время от 0,01 с на самой малой задаче до 1,5 с на полной.

В двух последних строках решатель за 10 минут не продвинулся дальше стартового решения; верхняя граница осталась около 100 %. Проценты в разных строках относятся к разным выборкам объектов и между собой напрямую не сравнимы.

### Весь город с сокращённым списком кандидатов

Все 19 519 объектов (все здания), 10 подразделений, кандидаты — случайная выборка.

| Кандидатов | Пар, млн | Время решателя | Память | Оптимум | Жадное добавление на той же выборке |
|---|---|---|---|---|---|
| 2 000 | 4,5 | 331 с | 6,1 ГБ | 90,23 % | 88,41 % |
| 5 000 | 11,1 | 28 с | 4,2 ГБ | 91,61 % | 90,49 % |
| 10 000 | 22,3 | 66 с | 7,7 ГБ | 91,65 % | 90,62 % |
| 20 000 | 44,4 | лимит | 13,7 ГБ | не решено | 90,06 % |
| 32 082 (все) | 71,1 | лимит | 13,8 ГБ | не решено | 90,19 % |

Здесь все строки относятся к одному набору объектов и сравнимы между собой.

### Зависимость от числа подразделений

Задача 10 000 × 10 000.

| Подразделений | Время решателя | Оптимум | Жадное добавление | Отставание |
|---|---|---|---|---|
| 5 | 26 с | 75,92 % | 73,05 % | 2,87 п. п. |
| 10 | 19 с | 91,70 % | 88,77 % | 2,93 п. п. |
| 20 | 70 с | 98,97 % | 97,78 % | 1,19 п. п. |
| 40 | 9 с | 100,00 % | 99,95 % | 0,05 п. п. |

**Что это значит.**

- Решатель «в лоб» справляется примерно до 26 миллионов пар «объект — кандидат». На 44 миллионах и больше за 10 минут он не выдаёт ничего полезного: 21,6 % против 90,2 % у жадного добавления.
- Сокращение списка кандидатов делает задачу для всего города решаемой. С 5 000 кандидатов оптимум найден за 28 секунд и равен 91,61 % — на 1,4 пункта выше жадного добавления на полном списке (90,19 %).
- Потеря от сокращения мала: переход от 5 000 к 10 000 кандидатов добавил 0,04 пункта. Оптимум для полного списка не получен, поэтому это вывод из сходимости цифр, а не из прямого сравнения.
- Время решателя не растёт плавно с размером: задача с 2 000 кандидатов считалась в 12 раз дольше, чем с 5 000. Планировать расчёт по размеру задачи нельзя.
- Жадное добавление отстаёт от оптимума на 1–3 пункта на всех размерах и при числе подразделений от 5 до 20; при 40 подразделениях разница исчезает.
- Память растёт на 0,3–0,5 ГБ на каждый миллион пар до тех пор, пока задача решается. Ограничением на 32 ГБ оперативной памяти стало время, а не память.
- Решатель начинал поиск с плохого решения, хотя жадное добавление за секунду даёт 90 %. Через `scipy.optimize.milp` передать ему стартовое решение нельзя; через прямой интерфейс HiGHS — можно.

## Ограничения

- Два графа: небольшой (эксперименты 1–3) и один крупный город (эксперимент 4).
- В экспериментах 1–3 целевые объекты — узлы графа с равным весом; в эксперименте 4 — здания, но без учёта их назначения и площади.
- По одному порогу на граф (5 и 10 минут) и одна метрика — доля прикрытых объектов.
- В эксперименте 4 на каждый размер взята одна случайная выборка объектов и кандидатов. При непредсказуемом времени решателя другая выборка может дать заметно другое время.
- Кандидаты отбирались случайно. Осмысленный отбор (по классу дорог, по пригодным участкам) может дать и меньший список, и лучший результат.
- Для полного списка кандидатов Красноярска нет ни оптимума, ни содержательной верхней границы.
- Генетический алгоритм запускался только с параметрами из документации и только на малом графе. С большим числом эпох он, вероятно, подойдёт ближе к оптимуму.
- Замеры времени выполнены по одному-два раза, без статистической обработки.
- Использован один решатель (HiGHS через `scipy`), без стартового решения и без настройки параметров.
- Имитация отжига не сравнивалась: для максимизируемых метрик она работает неверно (ошибка № 1 в `REDESIGN_GENESIS.MD`).

## Выводы для развития genesis

**1. Сделать матричную оценку на numpy основным способом расчёта состояния.**

Матрица хранится как массив numpy вместе с соответствием «узел → номер столбца»; оценка расстановки — минимум по выбранным столбцам. Имя первого прибывающего подразделения вычислять только по запросу: метрикам времени и прикрытия оно не нужно. Существующий `ArrivalTimeMatrixState` для этого не подходит: он даёт ускорение в 3 раза там, где возможно в 300.

**2. Считать матрицу через `scipy`.**

Замена расчёта в `get_atm` на `scipy.sparse.csgraph.dijkstra` даёт ускорение примерно в 20 раз без изменения результата. Вместе с расчётом по уникальным узлам (замечание Н6) это снимает главную претензию к матричному подходу — долгий предварительный расчёт.

**3. Добавить точный решатель как штатный алгоритм MCLP и LSCP.**

Реализация занимает около 15 строк (функция `solve_mclp` в приложении 1) и не требует новых зависимостей, кроме `scipy`. В рабочей версии нужны: фиксация существующих подразделений (`x_j = 1`), веса объектов, ограничение списка кандидатов и вариант для LSCP — минимум подразделений при заданном прикрытии.

Эксперимент 4 показывает, каким этот алгоритм должен быть, чтобы работать на городе:

- объекты группируются по узлам с весами — это сокращает задачу в разы без потери точности;
- список кандидатов сокращается до нескольких тысяч. Случайной выборки из 5 000 уже хватило, чтобы превзойти жадное добавление; осмысленный отбор должен быть не хуже;
- решатель запускается с лимитом времени и запасным вариантом. Если оптимум не найден, возвращается результат жадного добавления, а не то, на чём решатель остановился;
- жадное решение передаётся решателю как стартовое, чтобы результат в любом случае был не хуже него. Для этого нужен прямой интерфейс HiGHS (`highspy`) вместо `scipy.optimize.milp`.

**4. Жадное добавление оставить быстрым вариантом по умолчанию и дополнить шагом замены.**

Оно уже рекомендовано в документации, и эксперименты эту рекомендацию подтверждают: на полной задаче Красноярска оно отработало за 1,5 секунды там, где точный решатель не справился за 10 минут. Отставание в 1–3 пункта можно сократить перестановками «убрать одну точку — поставить другую» после жадного этапа.

**5. Пересмотреть место метаэвристик.**

Для метрик покрытия генетический алгоритм в нынешнем виде уступает и точному решателю, и жадному добавлению — по качеству и по времени. Его область — метрики, которые не записываются линейно, и пользовательские постановки. При этом ему нужны быстрая оценка (вывод 1) и исправления из `REDESIGN_GENESIS.MD`: разнообразная стартовая популяция, турнирный отбор, скрещивание без потери подразделений.

**6. Использовать точное решение как эталон в тестах и исследованиях.**

- В тестах: проверка вида «эвристика даёт не меньше N % от оптимума на тестовом графе» вместо порогов, подобранных вручную.
- В исследованиях: сравнивать алгоритмы по отставанию от оптимума. Это заменяет полный перебор, который возможен только для одного подразделения.

**7. Дополнить документацию правилом выбора алгоритма.**

Метрика покрытия и примерно до 25 миллионов пар «объект — кандидат» — точный решатель; задача больше — сократить кандидатов либо жадное добавление; метрика нелинейная — метаэвристики.

**8. Для городов крупнее Красноярска нужна декомпозиция и оценка сверху.**

Число пар растёт примерно пропорционально числу объектов: на один объект Красноярска приходится в среднем 3 640 кандидатов в пределах 10 минут, и это число определяется плотностью сети, а не размером города. Для города в несколько раз больше сокращения кандидатов, скорее всего, уже не хватит: чтобы сохранить ту же густоту кандидатов, их число придётся увеличивать вместе с городом. Это оценка, на таких данных она не проверялась. Тогда задача решается по районам с согласованием стыков, а качество результата оценивается верхней границей (например, релаксацией Лагранжа), которая считается и там, где оптимум недоступен.

## Что проверить следующим

1. **Отбор кандидатов.** Осмысленное сокращение списка (по классу дорог, по пригодным участкам, отбрасывание заведомо худших) вместо случайной выборки; несколько выборок на каждый размер.
2. **Стартовое решение.** Передача результата жадного добавления решателю через `highspy`: решается ли тогда полная задача Красноярска и как меняется время.
3. **Верхняя граница без точного решения** для полной задачи Красноярска.
4. **Декомпозиция по районам** и сравнение с решением для города целиком.
5. **Здания с весами по назначению и площади** вместо равных весов.
6. **LSCP.** Минимальное число подразделений для заданного прикрытия точным методом против результата `LSCP_ADD`.
7. **Среднее время прибытия** (задача p-медианы): точное решение на малом графе, обменный локальный поиск, генетический алгоритм.
8. **Генетический алгоритм при равном времени.** Сколько эпох нужно, чтобы догнать жадное добавление, и достижим ли оптимум при оценке на numpy.
9. **Имитация отжига** после исправления ошибки № 1.
10. **Повторные замеры времени** с усреднением.

## Приложение 1. Код экспериментов 1–3

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

## Приложение 2. Код эксперимента 4

Четыре файла и данные лежат в одном каталоге. Первый скрипт загружает данные из OpenStreetMap (около 135 МБ вместе с кэшем запросов), второй строит задачу, третий решает одну задачу заданного размера, четвёртый запускает список задач — каждую в отдельном процессе.

```
python download.py <каталог>
cd work/genesis
PYTHONPATH=. python <каталог>/prepare.py <каталог> 10

# рост размера задачи: объектов,кандидатов,подразделений,лимит (0 = все)
python <каталог>/run_list.py <каталог> python 2000,2000,10,600 5000,5000,10,600 10000,10000,10,600 15000,15000,10,600 0,20000,10,600 0,0,10,600

# сокращённый список кандидатов и разное число подразделений
python <каталог>/run_list.py <каталог> python 0,2000,10,600 0,5000,10,600 0,10000,10,600 10000,10000,5,600 10000,10000,20,600 10000,10000,40,600
```

Обе серии вместе занимают около 40 минут и до 14 ГБ оперативной памяти. При запуске за памятью решателя следил отдельный процесс с порогом остановки 24 ГБ; он не сработал ни разу.

### download.py

```python
"""Загрузка данных Красноярска из OpenStreetMap (по схеме из docs/pages/210_data_preparation)."""
import os
import sys
import time
import warnings

warnings.filterwarnings("ignore")

import osmnx as ox
import pandas as pd

OUT = sys.argv[1]
CITY = "Красноярск, Красноярский край, Россия"

ox.settings.use_cache = True
ox.settings.cache_folder = os.path.join(OUT, "cache")
ox.settings.requests_timeout = 600
ox.settings.default_access = ""  # как в документации проекта: не отбрасывать частные дороги
ox.settings.log_console = False


def step(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


step("границы города")
borders = ox.geocode_to_gdf(CITY)
row = borders.iloc[0]
step(f"  найдено: {row.get('display_name')} | тип: {row.get('addresstype')} / {row.get('class')}")
area_km2 = ox.projection.project_gdf(borders).area.iloc[0] / 1e6
step(f"  площадь: {area_km2:.0f} км²")
borders.to_file(os.path.join(OUT, "borders.gpkg"), driver="GPKG")

step("дорожная сеть (буфер 1000 м, drive_service, без упрощения)")
buf = ox.projection.project_gdf(borders).buffer(1000)
buf = ox.projection.project_gdf(buf, to_latlong=True)
t = time.time()
G = ox.graph_from_polygon(buf.union_all(), network_type="drive_service", simplify=False, retain_all=False)
step(f"  узлов: {G.number_of_nodes()}, рёбер: {G.number_of_edges()} ({time.time() - t:.0f} с)")
ox.save_graphml(G, os.path.join(OUT, "krasnoyarsk.graphml"))
step("  граф сохранён")

step("здания")
t = time.time()
b = ox.features_from_polygon(borders.union_all(), {"building": True})
b = b[b.geometry.geom_type.isin(["Polygon", "MultiPolygon"])]
step(f"  зданий: {len(b)} ({time.time() - t:.0f} с)")
c = ox.projection.project_gdf(b).geometry.centroid
c = ox.projection.project_gdf(c, to_latlong=True)
pd.DataFrame({"lon": c.x.values, "lat": c.y.values}).to_csv(os.path.join(OUT, "buildings_centroids.csv"), index=False)
step("готово")
```

### prepare.py

```python
"""Подготовка задачи MCLP для города: граф, объекты (здания по узлам), кандидаты, разреженная матрица покрытия."""
import json
import os
import sys
import time
import warnings

warnings.filterwarnings("ignore")

import geopandas as gpd
import networkx as nx
import numpy as np
import osmnx as ox
import pandas as pd
from scipy.sparse import csr_matrix, save_npz, vstack
from scipy.sparse.csgraph import dijkstra
from scipy.spatial import cKDTree

from fire_units.settings import DEFAULT_SPEEDS
from genesis.swiss_knife import DELAY_TIME
from graphs.speeds import kmh_to_mm, set_graph_travel_times

DATA = sys.argv[1]
T_COVER = float(sys.argv[2]) if len(sys.argv) > 2 else 10.0  # порог прикрытия, мин (с учётом задержки)
BATCH = 256


def step(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


info = {"T": T_COVER}

step("граф: загрузка, времена проезда, упрощение, наибольший сильносвязный компонент")
G = ox.load_graphml(os.path.join(DATA, "krasnoyarsk.graphml"))
info["nodes_raw"], info["edges_raw"] = G.number_of_nodes(), G.number_of_edges()
set_graph_travel_times(G, DEFAULT_SPEEDS, kmh_to_mm)
G = ox.simplify_graph(G)
info["nodes_simplified"] = G.number_of_nodes()
scc = max(nx.strongly_connected_components(G), key=len)
G = G.subgraph(scc).copy()
nodes = list(G.nodes())
n = len(nodes)
idx = {v: i for i, v in enumerate(nodes)}
info["nodes"], info["edges"] = n, G.number_of_edges()
step(f"  исходный: {info['nodes_raw']} узлов | упрощённый: {info['nodes_simplified']} | компонент: {n} узлов, {info['edges']} рёбер")

step("матрица смежности (из параллельных рёбер — самое быстрое)")
best = {}
for u, v, d in G.edges(data=True):
    key = (idx[u], idx[v])
    w = d["travel_time"]
    if isinstance(w, list):
        w = sum(w)
    if key not in best or w < best[key]:
        best[key] = w
rows, cols = zip(*best.keys())
A = csr_matrix((list(best.values()), (rows, cols)), shape=(n, n))
AT = A.T.tocsr()  # обратный граф: поиск от объекта даёт время «кандидат -> объект»

step("кандидаты: узлы в границах города")
g_nodes = ox.graph_to_gdfs(G, edges=False).loc[nodes]
borders = gpd.read_file(os.path.join(DATA, "borders.gpkg"))
in_city = g_nodes.within(borders.union_all()).to_numpy()
cand = np.flatnonzero(in_city)
info["candidates"] = int(len(cand))
step(f"  кандидатов: {len(cand)} из {n}")

step("объекты: здания, привязанные к ближайшему узлу")
b = pd.read_csv(os.path.join(DATA, "buildings_centroids.csv"))
pts = gpd.GeoSeries(gpd.points_from_xy(b["lon"], b["lat"]), crs="EPSG:4326")
g_proj = ox.projection.project_gdf(g_nodes)
pts = pts.to_crs(g_proj.crs)
tree = cKDTree(np.c_[g_proj.geometry.x, g_proj.geometry.y])
dist, near = tree.query(np.c_[pts.x, pts.y])
weights_all = np.bincount(near, minlength=n)
obj = np.flatnonzero(weights_all)
w = weights_all[obj].astype(float)
info.update(buildings=int(len(b)), objects=int(len(obj)), median_dist_m=float(np.median(dist)),
            share_over_300m=float((dist > 300).mean()))
step(f"  зданий: {len(b)} | узлов со зданиями (объектов): {len(obj)} | медиана расстояния до узла: {np.median(dist):.0f} м | дальше 300 м: {100 * (dist > 300).mean():.1f} %")

step(f"матрица покрытия: порог {T_COVER} мин (задержка {DELAY_TIME} мин входит)")
limit = T_COVER - DELAY_TIME
t0 = time.time()
blocks = []
for s in range(0, len(obj), BATCH):
    d = dijkstra(AT, directed=True, indices=obj[s:s + BATCH], limit=limit)
    blocks.append(csr_matrix(d[:, cand] <= limit))
    if (s // BATCH) % 10 == 0:
        print(f"    {s + BATCH}/{len(obj)}  {time.time() - t0:.0f} с", flush=True)
C = vstack(blocks, format="csr")
info.update(matrix_time_s=time.time() - t0, nnz=int(C.nnz), density=float(C.nnz / (C.shape[0] * C.shape[1])))
step(f"  готово за {info['matrix_time_s']:.0f} с | размер {C.shape[0]}x{C.shape[1]} | ненулевых: {C.nnz / 1e6:.1f} млн | плотность {100 * info['density']:.1f} %")

uncoverable = np.asarray(C.sum(axis=1)).ravel() == 0
info["uncoverable_buildings_share"] = float(w[uncoverable].sum() / w.sum())
step(f"  зданий, не достижимых за порог ни из одного кандидата: {100 * info['uncoverable_buildings_share']:.2f} %")

save_npz(os.path.join(DATA, "C.npz"), C)
np.save(os.path.join(DATA, "w.npy"), w)
json.dump(info, open(os.path.join(DATA, "info.json"), "w"), ensure_ascii=False, indent=1)
step("сохранено")
```

### solve_one.py

```python
"""Одна задача MCLP заданного размера: точный решатель и жадное добавление. Печатает JSON."""
import json
import resource
import sys
import time

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import csr_matrix, eye, hstack, load_npz

data, n_obj, n_cand, p, time_limit, seed = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4]), float(sys.argv[5]), int(sys.argv[6])

C = load_npz(f"{data}/C.npz").tocsr()
w = np.load(f"{data}/w.npy")
rng = np.random.default_rng(seed)
if n_obj and n_obj < C.shape[0]:
    r = np.sort(rng.choice(C.shape[0], n_obj, replace=False))
    C, w = C[r], w[r]
if n_cand and n_cand < C.shape[1]:
    c = np.sort(rng.choice(C.shape[1], n_cand, replace=False))
    C = C[:, c]
C = C.astype(float).tocsr()
n_o, n_c = C.shape
total = w.sum()


def covered(cols):
    return 100 * w[np.asarray(C[:, cols].sum(axis=1)).ravel() > 0].sum() / total


# Жадное добавление с весами
t0 = time.perf_counter()
left, cols_g, CT = np.ones(n_o), [], C.T.tocsr()
for _ in range(p):
    j = int(np.argmax(CT @ (w * left)))
    cols_g.append(j)
    left[C[:, j].nonzero()[0]] = 0
t_greedy = time.perf_counter() - t0

# Точный решатель
t0 = time.perf_counter()
cost = np.concatenate([np.zeros(n_c), -w])
cover = LinearConstraint(hstack([-C, eye(n_o)], format="csr"), -np.inf, 0)
count = LinearConstraint(csr_matrix(np.concatenate([np.ones(n_c), np.zeros(n_o)])[None, :]), p, p)
integrality = np.concatenate([np.ones(n_c), np.zeros(n_o)])
res = milp(cost, constraints=[cover, count], integrality=integrality, bounds=Bounds(0, 1),
           options={"time_limit": time_limit})
t_exact = time.perf_counter() - t0

out = dict(n_obj=n_o, n_cand=n_c, nnz=int(C.nnz), p=p, greedy=covered(cols_g), t_greedy=t_greedy,
           t_exact=t_exact, status=int(res.status), message=str(res.message)[:80],
           peak_gb=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1e9)
if res.x is not None:
    cols_e = list(np.flatnonzero(res.x[:n_c] > 0.5))
    out.update(exact=covered(cols_e), units=len(cols_e),
               bound=float(-res.mip_dual_bound * 100 / total) if getattr(res, "mip_dual_bound", None) is not None else None,
               gap=float(res.mip_gap) if getattr(res, "mip_gap", None) is not None else None)
print("RESULT " + json.dumps(out, ensure_ascii=False))
```

### run_list.py

```python
"""Запуск списка задач: аргументы вида объектов,кандидатов,p,лимит (0 = все). Каждая — в отдельном процессе."""
import subprocess
import sys
import time

data, py = sys.argv[1], sys.argv[2]
for cfg in sys.argv[3:]:
    n_obj, n_cand, p, tl = cfg.split(",")
    t0 = time.time()
    try:
        r = subprocess.run([py, f"{data}/solve_one.py", data, n_obj, n_cand, p, tl, "0"],
                           capture_output=True, text=True, timeout=float(tl) + 900)
        line = [l for l in r.stdout.splitlines() if l.startswith("RESULT ")]
        print(line[0] if line else f"FAIL {cfg}: код {r.returncode} | {r.stderr.strip()[-300:]}", flush=True)
    except subprocess.TimeoutExpired:
        print(f"TIMEOUT {cfg}: процесс остановлен через {time.time() - t0:.0f} с", flush=True)
```
