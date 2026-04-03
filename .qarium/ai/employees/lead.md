# Lead

## Architecture & Decisions
- **Go/JS loaders embed foreign-language source in Python docstrings** — avoids Go/JS FFI libraries, writes to tmpdir and runs as subprocess via `go run`/`node`
- **All language loaders inherit from abstract Loader base class** — shared interface with `collect()` → filter → `build()` → `compile()` pipeline via template method `load()`
- **Each calc domain has its own Stat/Status/Metric types** — complexity, RP, OP use different status scales; no shared types between domains
- **Click for CLI, radon for Python complexity** — radon is the standard Python cyclomatic complexity tool
- **reporters split into reporters/result.py + reporters/diff.py** — result reporters output analysis results, diff reporters compare two reports; shared via __init__.py re-exports
- **ProjectStat + ProjectDiff in statistics.py** — dataclass for project metrics snapshot + calculator for directional diffs (current - baseline); sign matters — positive means current is higher; used by diff reporters and compare CLI
- **Threshold supports imbalance checking via `abs(RP - OP)`** — `imbalance` threshold field validates balance between refactoring and overengineering pressure; uses key `IMB=` in CLI string format
- **Go and Kotlin use `class_loc_from_methods` flag** — both languages report method LOC independently, so class LOC is computed by summing method LOCs instead of counting class body lines; Swift does NOT use this flag because methods are inside type bodies
- **Swift uses tree-sitter for AST parsing** — unlike Go/JS/Kotlin which embed foreign-language source in Python docstrings and run as subprocess, Swift uses `tree-sitter` + `tree-sitter-swift` Python bindings for direct AST analysis; avoids external Swift toolchain dependency

## Project Structure
- **Language support in py/, go/, js/, kotlin/, swift/ — each with loader.py, collector.py, analyzer.py** — loader subclasses base Loader, collector gathers raw metrics, analyzer builds inheritance graph; swift/ uses tree-sitter instead of subprocess
- **Metrics calculation in calc/ — flat module + pressure/ sub-package** — complexity.py, score.py, pressure/refactoring.py, pressure/overengineering.py
- **Source model hierarchy in source.py without shared base class** — Sources → PackageSource → ModuleSource → ClassSource → MethodSource/FunctionSource, each with Status + compile()
- **Root __init__.py intentionally empty — all imports use fully-qualified strictacode.* path** — sub-packages re-export via __all__ (PyLoder, GoLoder, JSLoder, KotlinLoder, SwiftLoder, score, pressure, Complexity)

## Code Patterns
- **Absolute package-relative imports within strictacode/** — `from .calc import score`, `from strictacode.config import Config`
- **Subprocess failures raise RuntimeError(result.stderr)** — consistent pattern across Go/JS collectors and analyzers
- **CLI validation errors use click.UsageError** — not ValueError or custom exceptions
- **Private methods prefixed with single underscore, constants UPPER_SNAKE_CASE** — standard Python conventions
- **redirect_output() context manager in utils.py** — redirects stdout+stderr to file with auto-restore after block exit or exception, used by BaseResultReporter.report() and BaseDiffReporter.report()
- **Integration tests for external toolchains skip when tool not installed** — `pytestmark = pytest.mark.skipif(shutil.which("kotlinc") is None, ...)` pattern; ensures tests pass without requiring Go/Node/Kotlin SDK on CI

## TODO
- **Migrate existing `X | None` to `typing.Optional[X]`** — 30+ places in source.py, __main__.py, loader.py, config.py, calc/, reporters/ use PEP 604 syntax which fails at runtime on Python 3.10
- **Consolidate `class_loc_from_methods` conditions in `__main__.py`** — separate `if` blocks for GOLANG and KOTLIN set the same flag; merge into single `if config.lang in (Language.GOLANG, Language.KOTLIN)`

## LLM Directives
- **NEVER add `fetch-depth: 0` to CI without explicit reason** — MkDocs Material fetches repo metadata (version, stars) from GitHub API in the browser, git tags are not needed at build time
- **NEVER use PEP 604 `X | None` syntax in new files** — minimum supported Python is 3.10 where `X | None` in runtime annotations (dataclass fields) fails; always use `typing.Optional[X]` instead

## Lessons

| Problem | Why | How to prevent |
|---------|-----|----------------|
