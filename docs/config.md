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

## Взаимодействие с CLI

CLI-флаги `--top-*` перекрывают значения из конфигурационного файла:

```bash
# reporter.top.modules из конфига будет проигнорирован, использовано 20
strictacode analyze ./src --top-modules 20
```

Если CLI-флаг не указан — используется значение из конфига. Если конфиг отсутствует — используются дефолтные значения.