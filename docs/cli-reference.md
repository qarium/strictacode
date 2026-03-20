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
| `-o, --output`      | —       | Save output to a file instead of stdout         |
| `--threshold`       | —       | Fail if any metric exceeds the given threshold |

### Thresholds

The `--threshold` option enables quality gates. The command exits with code 1 if any specified metric exceeds its threshold.

**Single value** (applies to Project Score only):

```bash
strictacode analyze . --threshold 60
```

**Multiple metrics** (`key=value`, comma-separated):

```bash
strictacode analyze . --threshold score=60,rp=70,op=50,density=40
```

**Available keys:**

| Key         | Metric                     | Type   |
|-------------|----------------------------|--------|
| `score`     | Project Score              | int    |
| `rp`        | Refactoring Pressure       | int    |
| `op`        | Overengineering Pressure    | int    |
| `density`   | Complexity Density         | float  |

When a threshold is exceeded, the command prints an error and exits with code 1. All checks are performed — multiple thresholds can fail in a single run.

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

### Saving Output to File

Use `-o` / `--output` to save the report to a file:

```bash
strictacode analyze . --format json --output baseline.json
strictacode analyze . --output report.txt
```

The saved JSON file can be used as input for the `compare` command.

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

## `strictacode compare`

Compares two analysis results (JSON files) and shows the diff between their metrics.

```bash
strictacode compare RESULT_ONE RESULT_TWO [--threshold THRESHOLD]
```

### Arguments

| Argument      | Description                              |
|---------------|------------------------------------------|
| `RESULT_ONE`  | Path to the first JSON analysis result   |
| `RESULT_TWO`  | Path to the second JSON analysis result  |

### Options

| Option         | Default | Description                                      |
|----------------|---------|--------------------------------------------------|
| `--threshold`  | —       | Fail if the diff exceeds the given threshold     |

### Thresholds in Compare

When `--threshold` is specified, the command checks whether the difference between the two results exceeds the threshold. This is useful for CI/CD quality gates that block PRs if metrics degrade beyond an acceptable limit.

```bash
strictacode compare baseline.json current.json --threshold score=10,rp=5
```

The threshold syntax is the same as in `analyze` — see [Thresholds](#thresholds).

### Example

```bash
# Save baseline on main
strictacode analyze . --format json --output baseline.json

# After changes, save current state
strictacode analyze . --format json --output current.json

# Compare
strictacode compare baseline.json current.json
```

Output:
```
Result(baseline.json):
  * Score: 35
  * Complexity: 12.4
  * Refactoring: 55
  * Overengineering pressure: 20

---

Result(current.json):
  * Score: 42
  * Complexity: 14.1
  * Refactoring: 62
  * Overengineering pressure: 22

---

Diff:
  * Score: 7
  * Complexity density: 1.7
  * Refactoring pressure: 7
  * Overengineering pressure: 2
```

## Configuration File Loading

strictacode looks for a configuration file in the root of the analyzed project. Priority order:

1. `.strictacode.yml`
2. `.strictacode.yaml`
3. `.strictacode.json`

See [Configuration](configuration.md) for available options.
