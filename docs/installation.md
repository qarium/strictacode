# Installation

## Requirements

- **Python 3.10+**

Strictacode analyzes code written in:
- **Python** — no additional runtime required
- **Go** — requires `go` binary in `PATH`
- **JavaScript** — no additional runtime required

## Install from PyPI

```bash
pip install strictacode
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

## Next Steps

See the [Getting Started](getting-started.md) guide for a walkthrough of your first analysis.
