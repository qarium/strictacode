# Tech Writer

## Config

| Key           | Value                                                         | Description                        |
|---------------|---------------------------------------------------------------|------------------------------------|
| build_cmd     | `mkdocs build`                                                | Build validation command           |
| deploy_cmd    | `mkdocs gh-deploy --force`                                    | Deploy command                     |
| examples_file | `docs/examples.md`                                            | File for usage examples (optional) |
| logo_url      | `https://avatars.githubusercontent.com/u/262344922?s=200&v=4` | Header logo URL (optional)         |

## Rules

### Mapping

| Source path                     | Documentation files                                                                   |
|---------------------------------|---------------------------------------------------------------------------------------|
| `strictacode/__main__.py`       | `docs/cli-reference.md`, `docs/getting-started.md`, `docs/index.md`                   |
| `strictacode/config.py`         | `docs/configuration.md`, `docs/index.md`                                              |
| `strictacode/constants.py`      | `docs/cli-reference.md`, `docs/configuration.md`                                      |
| `strictacode/calc/**/*.py`      | `docs/metrics.md`, `docs/interpretation.md`, `docs/report-fields.md`, `docs/index.md` |
| `strictacode/analyzer.py`       | `docs/interpretation.md`, `docs/metrics.md`, `docs/index.md`                          |
| `strictacode/threshold.py`      | `docs/cli-reference.md`, `docs/examples.md`                                           |
| `strictacode/reporters/**/*.py` | `docs/cli-reference.md`, `docs/report-fields.md`                                      |
| `strictacode/statistics.py`     | `docs/report-fields.md`                                                               |
| `strictacode/source.py`         | `docs/report-fields.md`                                                               |
| `strictacode/graph.py`          | `docs/metrics.md`                                                                     |
| `strictacode/loader.py`         | `docs/configuration.md`                                                               |
| `strictacode/py/**/*.py`        | `docs/getting-started.md`, `docs/configuration.md`, `docs/index.md`                   |
| `strictacode/go/**/*`           | `docs/getting-started.md`, `docs/configuration.md`, `docs/index.md`                   |
| `strictacode/js/**/*`           | `docs/getting-started.md`, `docs/configuration.md`, `docs/index.md`                   |
| `strictacode/kotlin/**/*`       | `docs/getting-started.md`, `docs/configuration.md`, `docs/index.md`                   |
| `strictacode/skill.py`          | —                                                                                     |
| `strictacode/utils.py`          | —                                                                                     |
| `strictacode/__init__.py`       | —                                                                                     |
| `.github/actions/**`            | `docs/ci.md`, `docs/installation.md`, `docs/index.md`, `README.md`                    |
| `.github/workflows/**`          | `docs/ci.md`                                                                          |
| `.gitlab/templates/**`          | `docs/ci.md`                                                                          |

### Conventions

## Lessons

| Problem | Why | How to prevent |
|---------|-----|----------------|
