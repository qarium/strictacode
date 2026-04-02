# QA

## Config

| Setting          | Value                                              |
|------------------|----------------------------------------------------|
| run_tests_cmd    | `pytest --tb=short`                                |
| lint_cmd         | `ruff check strictacode/ tests/`                   |
| lint_fix_cmd     | `ruff check --fix strictacode/ tests/`             |
| format_cmd       | `ruff format --check strictacode/ tests/`          |
| format_fix_cmd   | `ruff format strictacode/ tests/`                  |

## Rules

Project-specific testing configuration. Used by the `employees-qa-feature` skill.

### Mapping

| Source path pattern             | Test directory     | Notes                            |
|---------------------------------|--------------------|----------------------------------|
| `strictacode/__main__.py`       | `tests/cli/`       | CLI commands                     |
| `strictacode/go/**/*`           | `tests/go/`        | Go loader and integration tests  |
| `strictacode/js/**/*`           | `tests/js/`        | JS loader and integration tests  |
| `strictacode/kotlin/**/*`       | `tests/kotlin/`    | Kotlin loader and integration tests |
| `strictacode/py/**/*.py`        | `tests/py/`        | Python loader tests              |
| `strictacode/calc/**/*.py`      | `tests/calc/`      | Calculation modules              |
| `strictacode/reporters/**/*.py` | `tests/reporters/` | `test_result.py`, `test_diff.py` |
| `strictacode/statistics.py`     | `tests/` (root)    | `test_statistics.py`             |
| `strictacode/utils.py`          | `tests/` (root)    | `test_utils.py`                  |
| `strictacode/threshold.py`      | `tests/` (root)    | `test_threshold.py`              |

### CLI Testing

Framework: `click.testing.CliRunner`
Entry point: `strictacode.__main__:app`
Test location: `tests/cli/test_cli.py`
Coverage: exit codes, stdout/stderr output, flag combinations, error messages on invalid input

### Mock Patterns

| Pattern                     | Example                                                              |
|-----------------------------|----------------------------------------------------------------------|
| Go subprocess collector     | `@patch("strictacode.go.collector.collect")`                         |
| Go subprocess analyzer      | `@patch("strictacode.go.analyzer.analyze")`                          |
| Kotlin subprocess collector | `@patch("strictacode.kotlin.collector.collect")`                     |
| Kotlin subprocess analyzer  | `@patch("strictacode.kotlin.analyzer.analyze")`                      |
| Python subprocess collector | `@patch("strictacode.py.collector.collect")`                         |
| Skill installation          | `monkeypatch.setattr("strictacode.__main__.skill.install", mock_fn)` |

### Helpers

| Helper                             | Location      | Purpose                                          |
|------------------------------------|---------------|--------------------------------------------------|
| `_write_go(tmp_path, name, code)`  | `tests/go/`   | Write Go package and return collect() result     |
| `_single_go(tmp_path, code)`       | `tests/go/`   | Write single Go file and return collect() result |
| `_write_js(tmp_path, name, code)`  | `tests/js/`   | Write JS file and return its directory           |
| `_single_func(tmp_path, code)`     | `tests/js/`   | Write single JS file and return collect() result |
| `_make_radon_json(root, filename)` | `tests/py/`   | Create radon-like JSON structure for mocks       |
| `_make_go_collector_json(root)`    | `tests/go/`   | Create go-collector-like JSON for mocks          |
| `_make_kotlin_collector_json(root)` | `tests/kotlin/` | Create Kotlin-collector-like JSON for mocks    |

### Conventions

- `# boundary: ...` comments at threshold transition edges in parametrize tables
- Never mock `builtins.open` — use `tmp_path` fixture instead
- Integration tests use `pytest.mark.skipif` when Go/Node.js/Kotlin SDK is unavailable

## Lessons

| Problem | Why | How to prevent |
|---------|-----|----------------|
