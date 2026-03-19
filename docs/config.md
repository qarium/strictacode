# Конфигурация

strictacode ищет конфигурационный файл в корне анализируемого проекта. Приоритет: `.strictacode.yml` > `.strictacode.yaml` > `.strictacode.json`.

## Опции

### lang

Язык проекта. Если не указан — определяется автоматически.

| Значение      | Описание  |
|---------------|-----------|
| `python`      | Python    |
| `golang`      | Go        |
| `javascript`  | JavaScript|

### loader.include

Список путей и директорий для анализа. Если указан — анализируются только файлы из этих путей. Пути указываются относительно корня проекта.

Если не указан — анализируются все файлы проекта (кроме исключённых через `exclude`).

```yaml
loader:
  include:
    - internal/
    - pkg/
```

### loader.exclude

Список путей и директорий, которые исключаются из анализа. Пути указываются относительно корня проекта.

```yaml
loader:
  exclude:
    - vendor/
    - generated/
    - internal/mock/
```

### reporter.top

Количество элементов в топе для каждой категории отчёта. Топ формируется по совокупности метрик (score, complexity, density, RP, OP).

| Опция      | Дефолт | Описание                |
|------------|--------|-------------------------|
| `packages` | 5      | Кол-во пакетов в топе   |
| `modules`  | 10     | Кол-во модулей в топе   |
| `classes`  | 20     | Кол-во классов в топе   |
| `methods`  | 25     | Кол-во методов в топе   |
| `functions`| 25     | Кол-во функций в топе   |

```yaml
reporter:
  top:
    packages: 5
    modules: 10
    classes: 20
    methods: 25
    functions: 25
```

## Примеры

### YAML (`.strictacode.yml`)

```yaml
lang: python

loader:
  include:
    - internal/
    - pkg/
  exclude:
    - migrations/
    - generated/

reporter:
  top:
    packages: 10
    modules: 20
```

### JSON (`.strictacode.json`)

```json
{
  "lang": "golang",
  "loader": {
    "include": ["internal/", "pkg/"],
    "exclude": ["vendor/", "generated/"]
  },
  "reporter": {
    "top": {
      "packages": 5,
      "modules": 15
    }
  }
}
```
