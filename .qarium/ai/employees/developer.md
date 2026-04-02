# Developer

## Config

| Setting     | Value                        |
|-------------|------------------------------|
| compile_cmd | python -m py_compile <file>  |

## Rules

### Conventions

| Rule | Description |
|------|-------------|
| typing alias | Use `import typing as t` instead of `from typing import ...` |
| No if/else in logic | Do not use if/else anywhere except module globals |
| No staticmethod classes | Classes with only static methods are modules — use modules instead |
| classmethod constructors | Use classmethod as alternative constructors (initializers) |
| No singleton classes | Singleton class is a module — use modules instead |
| LBYL over EAFP | Look Before You Leap is preferred over Easier to Ask Forgiveness |
| Relative imports | Use relative imports within the package |
| Aggregation over inheritance | Prefer aggregation/composition over inheritance |
| Docstrings in English | All docstrings must be written in English |
| Google-style docstrings | Use Google-style format: `Args:`, `Returns:`, `Raises:` sections with indented descriptions |

### Patterns

| Pattern | Description | Example |
|---------|-------------|---------|

## Lessons

| Problem | Why | How to prevent |
|---------|-----|----------------|