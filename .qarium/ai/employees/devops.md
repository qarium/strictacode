# DevOps

## Config

| Key            | Value          | Description                      |
|----------------|----------------|----------------------------------|
| ci_provider    | github-actions | CI provider                      |
| trigger_branch | main           | Default branch for triggers      |
| diff_range     | HEAD~5         | Git diff range for auto-analysis |

## Rules

### Workflow Registry

| Workflow | File                            | Trigger         | Purpose                  |
|----------|---------------------------------|-----------------|--------------------------|
| Lint     | `.github/workflows/lint.yml`    | push/PR to main | ruff check + format      |
| Tests    | `.github/workflows/tests.yml`   | push/PR to main | pytest + go + js matrix  |
| Docs     | `.github/workflows/docs.yml`    | push to master  | mkdocs gh-deploy         |
| Publish  | `.github/workflows/publish.yml` | tag v*          | PyPI release             |

### Conventions
