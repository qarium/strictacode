# DevOps

## Config

| Key            | Value          | Description                      |
|----------------|----------------|----------------------------------|
| ci_provider    | github-actions | CI provider                      |
| trigger_branch | master         | Default branch for triggers      |
| diff_range     | HEAD~5         | Git diff range for auto-analysis |

## Rules

### Workflow Registry

| Workflow    | File                                | Trigger           | Purpose                       |
|-------------|-------------------------------------|-------------------|-------------------------------|
| Lint        | `.github/workflows/lint.yml`        | push/PR to master | ruff check + format           |
| Tests       | `.github/workflows/tests.yml`       | push/PR to master | pytest + go + js matrix       |
| Docs        | `.github/workflows/docs.yml`        | push to master    | mkdocs gh-deploy              |
| Publish     | `.github/workflows/publish.yml`     | tag v*            | PyPI release                  |
| Strictacode | `.github/workflows/strictacode.yml` | push/PR to master | strictacode analyze + compare |

### Conventions

## Lessons

| Problem | Why | How to prevent |
|---------|-----|----------------|
| Fixed threshold quote bug in GitHub Actions but not in GitLab template | Project has CI templates for multiple providers (`.github/`, `.gitlab/`). Bug fix was scoped to the reported file only | When fixing a bug in one CI template, always search for the same pattern across all CI templates in the project before declaring the fix complete |
