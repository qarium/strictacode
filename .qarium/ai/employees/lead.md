# Lead

## Architecture & Decisions
- **Go/JS loaders embed foreign-language source in Python docstrings** — avoids Go/JS FFI libraries, writes to tmpdir and runs as subprocess via `go run`/`node`
- **All language loaders inherit from abstract Loader base class** — shared interface with `collect()` → filter → `build()` → `compile()` pipeline via template method `load()`
- **Each calc domain has its own Stat/Status/Metric types** — complexity, RP, OP use different status scales; no shared types between domains
- **Click for CLI, radon for Python complexity** — radon is the standard Python cyclomatic complexity tool
- **reporters split into reporters/result.py + reporters/diff.py** — result reporters output analysis results, diff reporters compare two reports; shared via __init__.py re-exports
- **ProjectStat + ProjectDiff in statistics.py** — dataclass for project metrics snapshot + calculator for absolute diffs (score, density, rp, op) used by diff reporters and compare CLI

## Project Structure
- **Language support in py/, go/, js/ — each with loader.py, collector.py, analyzer.py** — loader subclasses base Loader, collector gathers raw metrics, analyzer builds inheritance graph
- **Metrics calculation in calc/ — flat module + pressure/ sub-package** — complexity.py, score.py, pressure/refactoring.py, pressure/overengineering.py
- **Source model hierarchy in source.py without shared base class** — Sources → PackageSource → ModuleSource → ClassSource → MethodSource/FunctionSource, each with Status + compile()
- **Root __init__.py intentionally empty — all imports use fully-qualified strictacode.* path** — sub-packages re-export via __all__ (PyLoder, GoLoder, JSLoder, score, pressure, Complexity)

## Code Patterns
- **Absolute package-relative imports within strictacode/** — `from .calc import score`, `from strictacode.config import Config`
- **Subprocess failures raise RuntimeError(result.stderr)** — consistent pattern across Go/JS collectors and analyzers
- **CLI validation errors use click.UsageError** — not ValueError or custom exceptions
- **Private methods prefixed with single underscore, constants UPPER_SNAKE_CASE** — standard Python conventions
- **redirect_output() context manager in utils.py** — redirects stdout+stderr to file with auto-restore after block exit or exception, used by BaseResultReporter.report() and BaseDiffReporter.report()

## TODO
<!-- empty -->

## LLM Directives
- **NEVER add `fetch-depth: 0` to CI without explicit reason** — MkDocs Material fetches repo metadata (version, stars) from GitHub API in the browser, git tags are not needed at build time
