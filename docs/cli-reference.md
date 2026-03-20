# CLI Reference

## `strictacode analyze`

Analyzes a codebase and generates a quality report.

```bash
strictacode analyze PATH [OPTIONS]
```

### Arguments

| Argument | Description                                      |
|----------|--------------------------------------------------|
| `PATH`   | Absolute path to the project directory to analyze |

### Options

| Option              | Default | Description                                      |
|---------------------|---------|--------------------------------------------------|
| `--short`           | `false` | Show only project summary, skip packages/modules  |
| `--details`         | `false` | Include class, method, and function details       |
| `-f, --format`      | `text`  | Output format: `text` or `json`                  |
| `--top-packages`    | from config | Number of top packages to show             |
| `--top-modules`     | from config | Number of top modules to show              |
| `--top-classes`     | from config | Number of top classes to show              |
| `--top-methods`     | from config | Number of top methods to show              |
| `--top-functions`   | from config | Number of top functions to show            |

### Output Formats

**Text (default):**

```bash
strictacode analyze ./src
strictacode analyze ./src --short
strictacode analyze ./src --details
```

- `--short` — project-level summary only
- default — project + top packages + top modules
- `--details` — includes classes, methods, and functions

**JSON:**

```bash
strictacode analyze ./src --format json
```

Structured JSON with full metrics hierarchy. Suitable for CI/CD pipelines and programmatic processing.

### Error Handling

The command exits with an error if:
- The path does not exist
- The path is not a directory
- The language cannot be detected

## `strictacode install agent-skill`

Installs strictacode as a skill for AI coding assistants.

```bash
strictacode install agent-skill --agent AGENT [--name NAME]
```

### Options

| Option      | Default        | Description                                      |
|-------------|----------------|--------------------------------------------------|
| `--agent`   | *(required)*   | Target agent platform                            |
| `--name`    | `strictacode`  | Custom skill name                                |

### Supported Agents

| Agent         | Skill Path                              |
|---------------|-----------------------------------------|
| `claude`      | `~/.claude/skills/{name}/SKILL.md`      |
| `cursor`      | `~/.agents/skills/{name}/SKILL.md`      |
| `codex`       | `~/.codex/skills/{name}/SKILL.md`       |
| `gemini`      | `~/.agents/skills/{name}/SKILL.md`      |
| `antigravity` | `~/.agents/skills/{name}/SKILL.md`      |

### Example

```bash
strictacode install agent-skill --agent claude
```

## Configuration File Loading

strictacode looks for a configuration file in the root of the analyzed project. Priority order:

1. `.strictacode.yml`
2. `.strictacode.yaml`
3. `.strictacode.json`

See [Configuration](configuration.md) for available options.
