# Configuration

strictacode looks for a configuration file in the root of the analyzed project. Priority: `.strictacode.yml` > `.strictacode.yaml` > `.strictacode.json`.

## Options

### lang

The project language. If not specified, it is detected automatically.

| Value         | Description |
|---------------|-------------|
| `python`      | Python      |
| `golang`      | Go          |
| `javascript`  | JavaScript  |
| `kotlin`      | Kotlin      |
| `swift`       | Swift       |

### loader.include

A list of paths and directories to analyze. When specified, only files from these paths are analyzed. Paths are relative to the project root.

If not specified, all project files are analyzed (except those excluded via `exclude`).

```yaml
loader:
  include:
    - internal/
    - pkg/
```

### loader.exclude

A list of paths and directories to exclude from analysis. Paths are relative to the project root.

```yaml
loader:
  exclude:
    - vendor/
    - generated/
    - internal/mock/
```

### reporter.top

The number of entries in the top list for each report category. The ranking is based on a combination of metrics (score, complexity, density, RP, OP).

| Option      | Default | Description                     |
|-------------|---------|---------------------------------|
| `packages`  | 5       | Number of packages in the top   |
| `modules`   | 10      | Number of modules in the top    |
| `classes`   | 20      | Number of classes in the top    |
| `methods`   | 25      | Number of methods in the top    |
| `functions` | 25      | Number of functions in the top  |

```yaml
reporter:
  top:
    packages: 5
    modules: 10
    classes: 20
    methods: 25
    functions: 25
```

## Examples

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
