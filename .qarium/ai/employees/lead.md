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
- **Kotlin and Swift use tree-sitter for AST parsing** — unlike Go/JS which embed foreign-language source in Python docstrings and run as subprocess, Kotlin and Swift use `tree-sitter` + language bindings (`tree-sitter-kotlin`, `tree-sitter-swift`) for direct AST analysis; avoids external toolchain dependency; Kotlin collector uses dispatch table pattern (`_NODE_PARSERS`) instead of if/else chains
- **Kotlin, Swift and JS analyzers all use 5-pass algorithm for graph construction** — Pass 1 collects declarations and builds name→files map, Pass 2 resolves inheritance/conformance edges, Pass 3 collects imports (ES import + CJS require for JS, implicit conformance for Kotlin/Swift), Pass 4 extracts type usage and function calls, Pass 5 resolves usage edges against declared types
- **Kotlin and Swift use `_BASE_TYPES` frozenset to filter stdlib types from usage edges, Python does NOT** — Kotlin uses a Kotlin-specific type set, Swift uses a Swift-specific type set; Python analyzer was simplified to capture all uppercase constructor calls without stdlib filtering; `py/constants.py` was removed
- **JS analyzer registers functions and arrow functions as graph nodes** — `FunctionDeclaration` and `VariableDeclarator` with `FunctionExpression`/`ArrowFunctionExpression` initializers are added to the node set, enabling call graph edges between functions
- **JS analyzer collects imports for cross-file resolution** — `importMap` stores `localName → {targetRel, originalName}` with support for ES named/default/namespace imports, CJS destructured/member/default require, and aliased imports (`import { X as Y }`)

## Project Structure
- **Language support in py/, go/, js/, kotlin/, swift/ — each with loader.py, collector.py, analyzer.py** — loader subclasses base Loader, collector gathers raw metrics, analyzer builds inheritance graph; kotlin/ and swift/ use tree-sitter instead of subprocess
- **Kotlin and Swift share tools.py pattern** — each has a `tools.py` with `walk_<lang>_files()` generator that filters by extension, ignored dirs (`constants.IGNORED_DIRS`), and test suffixes; shared structure across tree-sitter languages
- **Metrics calculation in calc/ — flat module + pressure/ sub-package** — complexity.py, score.py, pressure/refactoring.py, pressure/overengineering.py
- **Source model hierarchy in source.py without shared base class** — Sources → PackageSource → ModuleSource → ClassSource → MethodSource/FunctionSource, each with Status + compile()
- **Root __init__.py intentionally empty — all imports use fully-qualified strictacode.* path** — sub-packages re-export via __all__ (PyLoder, GoLoder, JSLoder, KotlinLoder, SwiftLoder, score, pressure, Complexity)

## Code Patterns
- **Absolute package-relative imports within strictacode/** — `from .calc import score`, `from strictacode.config import Config`
- **Subprocess failures raise RuntimeError(result.stderr)** — consistent pattern across Go/JS collectors and analyzers
- **CLI validation errors use click.UsageError** — not ValueError or custom exceptions
- **Private methods prefixed with single underscore, constants UPPER_SNAKE_CASE** — standard Python conventions
- **Unused parameters prefixed with `_`** — when a function signature requires a parameter for interface compatibility but doesn't use it (e.g., `_nodes`, `_all_decls` in `_check_protocol_conformance`, `_node` in `visit_FunctionDef`), prefix with `_` to satisfy ruff ARG001/ARG002
- **Dispatch table pattern for node type parsing** — Kotlin collector uses `_NODE_PARSERS` dict populated at module end instead of if/else chains; new node types added as dict entries
- **redirect_output() context manager in utils.py** — redirects stdout+stderr to file with auto-restore after block exit or exception, used by BaseResultReporter.report() and BaseDiffReporter.report()
- **Integration tests for external toolchains skip when tool not installed** — `pytestmark = pytest.mark.skipif(shutil.which("kotlinc") is None, ...)` pattern; ensures tests pass without requiring Go/Node/Kotlin SDK on CI
- **Swift tree-sitter `user_type` wrapping requires recursive type extraction** — AST wraps type names in `user_type` → `type_identifier`, not as direct `type_identifier` children of `type_annotation` or `parameter`; use recursive `_collect_type_ids` helper to handle indirection when extracting type names
- **Tree-sitter constructor call detection differs between languages** — Swift uses `call_expression` → `simple_identifier`, Kotlin uses `call_expression` → `identifier`; both use uppercase-first-letter check and `_BASE_TYPES` filter to exclude stdlib types; NOT `constructor_expression`
- **JS analyzer uses stack-based scope tracking for call graph** — `nodeStack` with `enter/exit` visitors for `FunctionDeclaration`, `VariableDeclarator`, `ClassDeclaration`, `ClassExpression` tracks current context; `CallExpression`/`NewExpression` are attributed to the top of the stack

## TODO

## LLM Directives
- **NEVER add `fetch-depth: 0` to CI without explicit reason** — MkDocs Material fetches repo metadata (version, stars) from GitHub API in the browser, git tags are not needed at build time
- **NEVER use PEP 604 `X | None` syntax in new files** — minimum supported Python is 3.10 where `X | None` in runtime annotations (dataclass fields) fails; always use `typing.Optional[X]` instead
- **NEVER assume tree-sitter AST node types from documentation** — always verify with actual parse tree dumps; Swift tree-sitter node names differ from what grammar docs suggest (e.g., `call_expression` not `constructor_expression`, `user_type` wrapping `type_identifier`)

## Config

| Setting         | Value    |
|-----------------|----------|
| default_branch  | `0.0.x` |

## Lessons

| Problem | Why | How to prevent |
|---------|-----|----------------|
