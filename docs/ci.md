# CI/CD Integration

Strictacode provides ready-to-use integrations for GitHub Actions and GitLab CI. Both platforms support optional quality gates via environment variables — if no variables are set, the analysis runs without thresholds.

## GitHub Actions

Strictacode ships as a **composite action** that runs within your existing job.

### Basic Usage

```yaml
jobs:
  analyze:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - uses: actions/setup-python@v5
        with:
          python-version: "3.13"

      - uses: qarium/strictacode/.github/actions/analyze@v1
        env:
          STRICTACODE_SCORE: "60"
```

> **Important:** threshold env vars must be set as step-level `env`, not workflow-level `env`. Composite actions do not inherit the workflow env context.

### Action Inputs

| Input | Default | Description |
|-------|---------|-------------|
| `install-cmd` | `pip install strictacode` | Command to install strictacode |
| `working-directory` | `.` | Directory to analyze |

### What the Action Does

1. **All branches** — runs `strictacode analyze` with `--details` and optional absolute thresholds (`STRICTACODE_*`)
2. **Non-default branches only** — compares current code against the default branch with optional diff thresholds (`STRICTACODE_*_DIFF`)

The default branch is detected from the GitHub event context (`github.event.base_ref` for push, `github.event.base.ref` for pull requests), with a fallback to `github.event.repository.default_branch`.

### Threshold Variables

Set these as **step-level** `env` on the action:

**Absolute thresholds** — fail if the metric exceeds the value:

| Variable | Metric | Type |
|----------|--------|------|
| `STRICTACODE_SCORE` | Project Score | int |
| `STRICTACODE_RP` | Refactoring Pressure | int |
| `STRICTACODE_OP` | Overengineering Pressure | int |
| `STRICTACODE_IMB` | RP/OP Imbalance | int |
| `STRICTACODE_DENSITY` | Complexity Density | float |

**Diff thresholds** — fail if the diff from baseline exceeds the value (merge requests only):

| Variable | Metric | Type |
|----------|--------|------|
| `STRICTACODE_SCORE_DIFF` | Project Score change | int |
| `STRICTACODE_RP_DIFF` | Refactoring Pressure change | int |
| `STRICTACODE_OP_DIFF` | Overengineering Pressure change | int |
| `STRICTACODE_IMB_DIFF` | Imbalance change | int |
| `STRICTACODE_DENSITY_DIFF` | Complexity Density change | float |

### Full Example with All Options

```yaml
jobs:
  analyze:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - uses: actions/setup-python@v5
        with:
          python-version: "3.13"

      - uses: actions/cache@v4
        with:
          path: ~/.cache/pip
          key: ${{ runner.os }}-pip-${{ hashFiles('**/pyproject.toml') }}
          restore-keys: |
            ${{ runner.os }}-pip-

      - uses: qarium/strictacode/.github/actions/analyze@v1
        with:
          install-cmd: pip install strictacode
          working-directory: src
        env:
          STRICTACODE_SCORE: "60"
          STRICTACODE_RP: "70"
          STRICTACODE_SCORE_DIFF: "10"
          STRICTACODE_RP_DIFF: "5"
```

---

## GitLab CI

Strictacode provides a template that can be included via `include: remote` directly from GitHub.

### Basic Usage

```yaml
include:
  - remote: 'https://raw.githubusercontent.com/qarium/strictacode/master/.gitlab/templates/strictacode.yml'

variables:
  STRICTACODE_SCORE: "60"
```

### Configuration Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `STRICTACODE_IMAGE` | `python:3.13` | Docker image for the job |
| `STRICTACODE_WORK_DIR` | `.` | Directory to analyze |
| `STRICTACODE_INSTALL_CMD` | `pip install strictacode` | Install command |

### What the Template Does

Two jobs are defined:

- **`strictacode-analyze`** — runs on merge requests and the default branch push. Uses `--details` and optional absolute thresholds.
- **`strictacode-compare`** — runs on merge requests only. Compares current code against the default branch with optional diff thresholds. Uses GitLab artifacts to pass the analysis result between jobs.

### Threshold Variables

Same threshold variables as GitHub Actions (`STRICTACODE_*` for absolute, `STRICTACODE_*_DIFF` for diff). Set them in the `variables` section or as CI/CD variables in GitLab project settings.

### Custom Stage

Both jobs use `stage: test` by default. You can override the stage when including the template — YAML anchors are used for shared configuration, so the job-level `stage` key takes precedence:

```yaml
include:
  - remote: 'https://raw.githubusercontent.com/qarium/strictacode/master/.gitlab/templates/strictacode.yml'

variables:
  STRICTACODE_SCORE: "60"
  STRICTACODE_RP_DIFF: "5"

strictacode-analyze:
  stage: quality
strictacode-compare:
  stage: quality
```

### Full Example

```yaml
include:
  - remote: 'https://raw.githubusercontent.com/qarium/strictacode/master/.gitlab/templates/strictacode.yml'

variables:
  STRICTACODE_IMAGE: "python:3.13"
  STRICTACODE_WORK_DIR: "src"
  STRICTACODE_SCORE: "60"
  STRICTACODE_RP: "70"
  STRICTACODE_SCORE_DIFF: "10"
```

---

## How Thresholds Work

When threshold variables are set, the CI job fails (non-zero exit code) if any specified metric exceeds its value. The full analysis report is printed to the log before the job exits.

**Without thresholds** — analysis runs in report-only mode, the job always succeeds.

**With absolute thresholds** — the job fails if the current metric value exceeds the threshold.

**With diff thresholds** (merge requests only) — the job fails if the change from the baseline branch exceeds the threshold. This prevents metrics from regressing beyond an acceptable limit.
