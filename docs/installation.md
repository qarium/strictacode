# Installation

## Requirements

- **Python 3.10+**

Strictacode analyzes code written in:
- **Python** — no additional runtime required
- **Go** — requires `go` binary in `PATH`
- **JavaScript** — requires `node` and `npm` in `PATH`, plus globally installed `@babel/parser` and `@babel/traverse`:

  ```bash
  npm install -g @babel/parser @babel/traverse
  ```
- **Kotlin** — requires `kotlinc` binary in `PATH`

## Install from PyPI

```bash
pip install strictacode
```

or with [uv](https://docs.astral.sh/uv/):

```bash
uv pip install strictacode
```

or as a project dependency:

```bash
uv add strictacode
```

## Verify Installation

```bash
strictacode analyze . --short
```

If everything is installed correctly, you'll see a report with your project's health metrics.

## AI Agent Integration

Install strictacode as a skill in your AI agent:

```bash
strictacode install agent-skill --agent <name>
```

Supported agents: `claude`, `cursor`, `codex`, `gemini`, `antigravity`

For full command options see the [CLI Reference](cli-reference.md#strictacode-install-agent-skill).

## CI/CD Integration

Strictacode provides ready-to-use integrations for [GitHub Actions](ci.md#github-actions) and [GitLab CI](ci.md#gitlab-ci). Both support optional quality gates via environment variables.

## Next Steps

See the [Getting Started](getting-started.md) guide for a walkthrough of your first analysis.
