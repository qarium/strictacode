# DevOps

## Config

| Key            | Value          | Description                      |
|----------------|----------------|----------------------------------|
| ci_provider    | github-actions | CI provider                      |
| trigger_branch | 0.0.x          | Default branch for triggers      |
| diff_range     | HEAD~5         | Git diff range for auto-analysis |

## Rules

### Workflow Registry

| Workflow    | File                                | Trigger            | Purpose                                        |
|-------------|-------------------------------------|--------------------|------------------------------------------------|
| Lint        | `.github/workflows/lint.yml`        | push/PR to 0.0.x   | ruff check via ruff-action + ruff format check |
| Tests       | `.github/workflows/tests.yml`       | push/PR to 0.0.x   | pytest matrix: Python 3.10–3.14, Go 1.22–1.24, Node 18–22; Kotlin/Swift via tree-sitter |
| Docs        | `.github/workflows/docs.yml`        | push to 0.0.x      | mkdocs gh-deploy                               |
| Publish     | `.github/workflows/publish.yml`     | workflow_dispatch  | Caller: `qarium/ci` library-publish reusable workflow |
| Strictacode | `.github/workflows/strictacode.yml` | push/PR to 0.0.x   | strictacode analyze + compare via composite action |
| New Version | `.github/workflows/new_version.yml` | workflow_dispatch  | Caller: `qarium/ci` library-new-version reusable workflow |

### Conventions

- Lint uses `astral-sh/ruff-action` for check + explicit `ruff format --check` step
- Kotlin and Swift tests run via tree-sitter without external SDK
- Publish and New Version use caller pattern via `qarium/ci` reusable workflows
- Pip cache shared across workflows via `actions/cache@v4` with `pyproject.toml` hash key
- Strictacode uses composite action `.github/actions/analyze`

## Lessons

| Problem                                                                | Why                                                                                                                    | How to prevent                                                                                                                                    |
|------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------|
| Fixed threshold quote bug in GitHub Actions but not in GitLab template | Project has CI templates for multiple providers (`.github/`, `.gitlab/`). Bug fix was scoped to the reported file only | When fixing a bug in one CI template, always search for the same pattern across all CI templates in the project before declaring the fix complete |
