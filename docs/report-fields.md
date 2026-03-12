# Поля отчёта strictacode

Этот документ описывает все поля, которые выводятся в отчёте strictacode для каждого уровня иерархии кода.

---

## Уровни отчёта

```
Project
├── Package[]
│   └── Module[]
│       ├── Class[]
│       │   └── Method[]
│       └── Function[]
```

---

## Project

Корневой уровень отчёта. Описывает весь проект целиком.

### Общие поля

| Поле        | Тип      | Описание                                                                            |
|-------------|----------|-------------------------------------------------------------------------------------|
| `lang`      | `string` | Язык программирования проекта. Возможные значения: `python`, `golang`, `javascript` |
| `loc`       | `int`    | Общее количество строк кода в проекте (без комментариев и пустых строк)             |
| `packages`  | `int`    | Количество пакетов в проекте                                                        |
| `modules`   | `int`    | Количество модулей (файлов) в проекте                                               |
| `classes`   | `int`    | Количество классов в проекте                                                        |
| `methods`   | `int`    | Количество методов в проекте                                                        |
| `functions` | `int`    | Количество функций верхнего уровня в проекте                                        |

### status

Статус здоровья проекта.

| Поле | Тип | Описание |
|------|-----|----------|
| `name` | `string` | Название статуса. Возможные значения: `healthy`, `normal`, `warning`, `critical`, `emergency` |
| `score` | `int` | Общая оценка здоровья проекта (0-100). Чем ниже — тем здоровее код |
| `reasons` | `string[]` | Список причин текущего статуса (опционально) |
| `suggestions` | `string[]` | Список рекомендаций по улучшению (опционально) |

**Шкала status.name:**

| Score | Статус | Интерпретация |
|-------|--------|---------------|
| 0-20 | `healthy` | Код здоров |
| 21-40 | `normal` | Нормальное состояние |
| 41-60 | `warning` | Есть проблемы |
| 61-80 | `critical` | Критическое состояние |
| 81-100 | `emergency` | Экстренная ситуация |

### overengineering_pressure

Метрика избыточной сложности архитектуры.

| Поле | Тип | Описание |
|------|-----|----------|
| `score` | `int` | Значение Overengineering Pressure (0-100) |
| `stat(modules)` | `Stat` | Статистика по модулям (см. раздел Stat) |

**Шкала score:**

| Score | Статус | Интерпретация |
|-------|--------|---------------|
| 0-20 | `simple` | Простая архитектура |
| 21-40 | `moderate` | Умеренная сложность |
| 41-60 | `complex` | Много абстракций |
| 61-80 | `overengineered` | Явный overengineering |
| 81-100 | `bloated` | Архитектура блокирует разработку |

### refactoring_pressure

Метрика давления на рефакторинг.

| Поле | Тип | Описание |
|------|-----|----------|
| `score` | `int` | Значение Refactoring Pressure (0-100) |
| `stat(modules)` | `Stat` | Статистика по модулям (см. раздел Stat) |

**Шкала score:**

| Score | Статус | Интерпретация |
|-------|--------|---------------|
| 0-20 | `minimal` | Код чистый |
| 21-40 | `low` | Есть проблемные места |
| 41-60 | `medium` | Техдолг влияет на скорость |
| 61-80 | `high` | Разработка замедлена |
| 81-100 | `extreme` | Код блокирует работу |

### complexity

Метрика сложности кода.

| Поле | Тип | Описание |
|------|-----|----------|
| `score` | `int` | Суммарная цикломатическая сложность |
| `density` | `float` | Плотность сложности: `(score / loc) * 100` |
| `stat(modules)` | `Stat` | Статистика по модулям (см. раздел Stat) |

**Шкала density:**

| Density | Статус | Интерпретация |
|---------|--------|---------------|
| 0-10 | `clean` | Простой код |
| 11-20 | `good` | Нормальная сложность |
| 21-30 | `moderate` | Есть сложные места |
| 31-50 | `dirty` | Много ветвлений |
| 51-75 | `very-dirty` | Спагетти-код |
| 76-100 | `spaghetti` | Сложно менять |
| 100+ | `unreadable` | Нужна переработка |

---

## Package

Пакет — логическая группировка модулей (директория).

| Поле | Тип | Описание |
|------|-----|----------|
| `name` | `string` | Название пакета (имя директории) |
| `dir` | `string` | Путь к директории пакета |
| `loc` | `int` | Количество строк кода в пакете |
| `modules` | `int` | Количество модулей в пакете |
| `status` | `Status` | Статус здоровья пакета (структура аналогична Project.status) |
| `overengineering_pressure` | `MetricWithStat` | Overengineering Pressure пакета |
| `refactoring_pressure` | `MetricWithStat` | Refactoring Pressure пакета |
| `complexity` | `ComplexityWithStat` | Сложность пакета |

### overengineering_pressure (Package)

| Поле | Тип | Описание |
|------|-----|----------|
| `score` | `int` | Значение Overengineering Pressure (0-100) |
| `stat(modules)` | `Stat` | Статистика по модулям пакета |

### refactoring_pressure (Package)

| Поле | Тип | Описание |
|------|-----|----------|
| `score` | `int` | Значение Refactoring Pressure (0-100) |
| `stat(modules)` | `Stat` | Статистика по модулям пакета |

### complexity (Package)

| Поле | Тип | Описание |
|------|-----|----------|
| `score` | `int` | Суммарная сложность |
| `density` | `float` | Плотность сложности |
| `stat(modules)` | `Stat` | Статистика по модулям пакета |

---

## Module

Модуль — отдельный файл с исходным кодом.

| Поле | Тип | Описание |
|------|-----|----------|
| `name` | `string` | Название модуля (имя файла) |
| `file` | `string` | Путь к файлу |
| `loc` | `int` | Количество строк кода в модуле |
| `classes` | `int` | Количество классов в модуле |
| `functions` | `int` | Количество функций верхнего уровня в модуле |
| `status` | `Status` | Статус здоровья модуля |
| `overengineering_pressure` | `MetricWithStat` | Overengineering Pressure модуля |
| `refactoring_pressure` | `MetricSimple` | Refactoring Pressure модуля (только score) |
| `complexity` | `ComplexityWithStat` | Сложность модуля |

### overengineering_pressure (Module)

| Поле | Тип | Описание |
|------|-----|----------|
| `score` | `int` | Значение Overengineering Pressure (0-100) |
| `stat(classes)` | `Stat` | Статистика по классам модуля |

### refactoring_pressure (Module)

| Поле | Тип | Описание |
|------|-----|----------|
| `score` | `int` | Значение Refactoring Pressure (0-100) |

### complexity (Module)

| Поле | Тип | Описание |
|------|-----|----------|
| `score` | `int` | Суммарная сложность классов и функций |
| `density` | `float` | Плотность сложности модуля |
| `stat(classes+functions)` | `Stat` | Статистика по классам и функциям модуля |

---

## Class

Класс в объектно-ориентированном коде.

| Поле | Тип | Описание |
|------|-----|----------|
| `name` | `string` | Название класса |
| `file` | `string` | Путь к файлу, содержащему класс |
| `loc` | `int` | Количество строк кода в классе |
| `methods` | `int` | Количество методов в классе |
| `status` | `Status` | Статус здоровья класса |
| `overengineering_pressure` | `MetricSimple` | Overengineering Pressure класса |
| `complexity` | `ComplexityWithStat` | Сложность класса |

### overengineering_pressure (Class)

| Поле | Тип | Описание |
|------|-----|----------|
| `score` | `int` | Значение Overengineering Pressure (0-100). Основано на fan-out, fan-in, depth, centrality в графе зависимостей |

### complexity (Class)

| Поле | Тип | Описание |
|------|-----|----------|
| `score` | `int` | Суммарная сложность методов класса |
| `density` | `float` | Плотность сложности класса |
| `stat(methods)` | `Stat` | Статистика по методам класса |

---

## Method

Метод класса.

| Поле | Тип | Описание |
|------|-----|----------|
| `name` | `string` | Название метода |
| `file` | `string` | Путь к файлу, содержащему метод |
| `class` | `string` | Название класса, к которому принадлежит метод |
| `loc` | `int` | Количество строк кода в методе |
| `closures` | `int` | Количество вложенных функций (closures) в методе |
| `status` | `Status` | Статус здоровья метода |
| `complexity` | `ComplexityFunc` | Сложность метода |

### complexity (Method)

| Поле | Тип | Описание |
|------|-----|----------|
| `score` | `int` | Цикломатическая сложность метода |
| `total` | `int` | Общая сложность метода включая closures |
| `density` | `float` | Плотность сложности: `(score / loc) * 100` |
| `stat(closures)` | `Stat` | Статистика по вложенным closures |

---

## Function

Функция верхнего уровня (не метод класса).

| Поле | Тип | Описание |
|------|-----|----------|
| `name` | `string` | Название функции |
| `file` | `string` | Путь к файлу, содержащему функцию |
| `loc` | `int` | Количество строк кода в функции |
| `closures` | `int` | Количество вложенных функций в теле функции |
| `status` | `Status` | Статус здоровья функции |
| `complexity` | `ComplexityFunc` | Сложность функции |

### complexity (Function)

| Поле | Тип | Описание |
|------|-----|----------|
| `score` | `int` | Цикломатическая сложность функции |
| `total` | `int` | Общая сложность функции включая closures |
| `density` | `float` | Плотность сложности: `(score / loc) * 100` |
| `stat(closures)` | `Stat` | Статистика по вложенным closures |

---

## Общие структуры

### Stat

Статистика по дочерним элементам. Используется во всех уровнях отчёта.

| Поле | Тип | Описание |
|------|-----|----------|
| `avg` | `int` | Среднее значение |
| `min` | `int` | Минимальное значение |
| `max` | `int` | Максимальное значение |
| `p50` | `int` | Медиана (50-й перцентиль) |
| `p90` | `int` | 90-й перцентиль |

**Пример:**
```
stat(modules):
  + avg: 8
  + min: 1
  + max: 24
  + p50: 6
  + p90: 16
```

### Status

Структура статуса здоровья. Одинакова для всех уровней.

| Поле | Тип | Описание |
|------|-----|----------|
| `name` | `string` | Название статуса |
| `score` | `int` | Числовое значение (0-100) |
| `reasons` | `string[]` | Причины текущего статуса (опционально) |
| `suggestions` | `string[]` | Рекомендации по улучшению (опционально) |

**Шкала status.name:**

| Score | Статус | Интерпретация |
|-------|--------|---------------|
| 0-20 | `healthy` | Код здоров |
| 21-40 | `normal` | Нормальное состояние |
| 41-60 | `warning` | Есть проблемы |
| 61-80 | `critical` | Критическое состояние |
| 81-100 | `emergency` | Экстренная ситуация |

---

## Форматы отчёта

### Text (по умолчанию)

```bash
strictacode analyze ./src
strictacode analyze ./src --short
strictacode analyze ./src --details
```

- `--short` — только Project уровень
- по умолчанию — Project + Packages + Modules
- `--details` — включает Class, Method, Function уровни

### JSON

```bash
strictacode analyze ./src --format json
```

Возвращает структуру с полями, соответствующими описанным выше.

---

## Пример отчёта

```
Project:
  * lang: python
  * loc: 3235
  * packages: 6
  * modules: 20
  * classes: 34
  * methods: 153
  * functions: 36
  * status:
    - name: healthy
    - score: 18
  * overengineering_pressure:
    - score: 8
    - stat(modules):
      + avg: 3
      + min: 0
      + max: 9
      + p50: 2
      + p90: 8
  * refactoring_pressure:
    - score: 34
    - stat(modules):
      + avg: 8
      + min: 1
      + max: 24
      + p50: 6
      + p90: 16
  * complexity:
    - score: 242
    - density: 7.48
    - stat(modules):
      + avg: 12
      + min: 2
      + max: 52
      + p50: 6
      + p90: 26

---

Packages:
  * strictacode:
    - dir: strictacode
    - loc: 1429
    - modules: 7
    - status:
      + name: healthy
      + score: 19
    - overengineering_pressure:
      + score: 9
      + stat(modules):
        - avg: 1
        - min: 0
        - max: 5
        - p50: 0
        - p90: 4
    - refactoring_pressure:
      + score: 34
      + stat(modules):
        - avg: 8
        - min: 3
        - max: 24
        - p50: 6
        - p90: 15
    - complexity:
      + score: 104
      + density: 7.28
      + stat(modules):
        - avg: 15
        - min: 2
        - max: 52
        - p50: 7
        - p90: 32

---

Modules:
  * utils.py:
    - file: strictacode/utils.py
    - loc: 112
    - classes: 0
    - functions: 7
    - status:
      + name: healthy
      + score: 19
    - overengineering_pressure:
      + score: 0
      + stat(classes):
        - avg: 0
        - min: 0
        - max: 0
        - p50: 0
        - p90: 0
    - refactoring_pressure:
      + score: 24
    - complexity:
      + score: 52
      + density: 46.43
      + stat(classes+functions):
        - avg: 7
        - min: 4
        - max: 14
        - p50: 8
        - p90: 11

---

Classes:
  * Metric:
    - file: strictacode/calc/score.py
    - loc: 16
    - methods: 2
    - status:
      + name: normal
      + score: 21
    - overengineering_pressure:
      + score: 0
    - complexity:
      + score: 6
      + density: 37.5
      + stat(methods):
        - avg: 5
        - min: 5
        - max: 5
        - p50: 5
        - p90: 5

---

Methods:
  * number_of_edges:
    - file: strictacode/graph.py
    - class: DiGraph
    - loc: 2
    - closures: 0
    - status:
      + name: warning
      + score: 60
    - complexity:
      + score: 2
      + total: 2
      + density: 100.0
      + stat(closures):
        - avg: 0
        - min: 0
        - max: 0
        - p50: 0
        - p90: 0

---

Functions:
  * lines_of_code:
    - file: strictacode/utils.py
    - loc: 35
    - closures: 1
    - status:
      + name: normal
      + score: 29
    - complexity:
      + score: 14
      + total: 17
      + density: 40.0
      + stat(closures):
        - avg: 3
        - min: 3
        - max: 3
        - p50: 3
        - p90: 3
```