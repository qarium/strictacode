# Developer

## Config

| Setting     | Value                        |
|-------------|------------------------------|
| compile_cmd | python -m py_compile <file>  |

## Rules

### Conventions

| Rule                         | Description                                                                                                                                                         |
|------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| constants module             | Constants-only modules must be imported as a whole (`import constants`) and accessed via `constants.NAME`                                                           |
| typed constants              | All constants must be typed with `t.Final` or `t.Final[<type>]`                                                                                                     |
| typed signatures             | All function/method signatures must have type annotations for parameters and return types                                                                           |
| Python 3.10 compat           | Code must run on Python 3.10+ — use `t.Optional[X]` instead of `X | None`, `t.Union` instead of `X | Y` in runtime contexts (dataclass fields, function defaults)   |
| typing alias                 | Use `import typing as t` instead of `from typing import ...`                                                                                                        |
| No if/else in logic          | Do not use if/else anywhere except module globals                                                                                                                   |
| No staticmethod classes      | Classes with only static methods are modules — use modules instead                                                                                                  |
| classmethod constructors     | Use classmethod as alternative constructors (initializers)                                                                                                          |
| No singleton classes         | Singleton class is a module — use modules instead                                                                                                                   |
| LBYL over EAFP               | Look Before You Leap is preferred over Easier to Ask Forgiveness                                                                                                    |
| Relative imports             | Use relative imports within the package                                                                                                                             |
| Aggregation over inheritance | Prefer aggregation/composition over inheritance                                                                                                                     |
| Docstrings in English        | All docstrings must be written in English                                                                                                                           |
| Google-style docstrings      | Use Google-style format: `Args:`, `Returns:`, `Raises:` sections with indented descriptions                                                                         |
| Visual block separation      | Separate logical blocks inside functions with a blank line: control flow (`if`, `for`, `while`, `with`, `try`), `return`, `raise`, and groups of related statements |
| Mandatory docstrings         | All classes, functions, and methods must have docstrings                                                                                                            |

### Patterns

| Pattern                 | Description                                                                       | Example                                 |
|-------------------------|-----------------------------------------------------------------------------------|-----------------------------------------|
| Language package layout | Constants in `constants.py` (import whole module), helper functions in `tools.py` | `swift/constants.py` + `swift/tools.py` |

## Lessons

| Problem                                 | Why                                                                                                   | How to prevent                                                             |
|-----------------------------------------|-------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------|
| common.py mixes constants and functions | Mixing concerns in one module hurts composition — constants and helpers have different reuse patterns | Separate into `constants.py` (import whole) + `tools.py` (import specific) |
| Kotlin collector had if/elif in tree traversal | Using if/elif chain for AST node types prevents processing nested nodes (e.g., binary_expression inside if_expression) — elif stops traversal | Use independent `if` checks for each node type, always recurse into children after checks |
| Kotlin collector duplicated body extraction | `_parse_class_declaration` and `_parse_object_declaration` had identical body extraction and method iteration loops | Extract shared `_extract_type_body` and `_extract_methods` helpers |
