**Codebase health diagnostics.**

Strictacode identifies your project's pain points: spaghetti code, overengineering, and complexity that blocks development.

> Works with AI agents for automated code quality analysis.

> Easily integrates into CI/CD pipelines and your local REPL development loop.

## Supported Languages

Golang · Python · JavaScript

## Quick Start

```bash
pip install strictacode
strictacode analyze . --short
```

Results unclear? See [Metric Interpretation](interpretation.md) for scenarios and recommendations.

## Why This Exists

Have you ever opened a legacy project and thought: *where do I even start?*
Or looked at a test coverage report and realized: *this doesn't show the real problem*.

Strictacode answers the question: **how painful is it to work with this code?**

It doesn't count lines. It looks for:
- Functions that are hard to change without introducing bugs
- Architecture that is overly complex for the task at hand
- Places where technical debt is already blocking development

## How It Works

```
$ strictacode analyze ./src --short

Project:
  * status:
    - name: warning
    - score: 58          ← project health (0–100, lower = better)
  * refactoring_pressure:
    - score: 72          ← how much the code "pressures" the developer
  * overengineering_pressure:
    - score: 18          ← how excessive the architecture is
  * complexity:
    - density: 42.5      ← complexity concentration
```

This tells you:
- **Spaghetti** (high RP, low OP) → clean up functions
- **Overengineering** (high OP, low RP) → simplify architecture
- **Crisis** (both high) → isolate and rewrite
- **Healthy** (both low) → keep monitoring

## Metrics

| Metric                       | What it measures          | Good   | Bad    |
|------------------------------|---------------------------|--------|--------|
| **Project Score**            | Overall health            | 0–20   | 60+    |
| **Refactoring Pressure**     | Pressure to refactor      | 0–40   | 60+    |
| **Overengineering Pressure** | Excessive complexity      | 0–40   | 60+    |
| **Complexity Density**       | Complexity concentration  | < 20   | > 50   |

## When to Use

| Situation               | What strictacode provides                               |
|-------------------------|----------------------------------------------------------|
| Technical debt audit    | Turns "the code is bad" into metrics for management     |
| Test planning           | Points out which projects/components need more attention|
| Refactoring planning    | Shows where "80% of pain comes from 20% of code"        |
| Sprint retrospective    | Objective data instead of subjective opinions            |
| Project onboarding      | Highlights the most complex modules                      |
| CI/CD pipeline          | Blocks quality degradation with GitHub Actions or GitLab CI |

## Commands

```bash
# Full report
strictacode analyze <path>

# Short report
strictacode analyze <path> --short

# Breakdown by modules, classes, functions
strictacode analyze <path> --details

# JSON output for CI/CD
strictacode analyze <path> --format json
```

## AI Agent Integration

Strictacode can be installed as a skill in AI agents for automated code quality analysis:

```bash
strictacode install agent-skill --agent <agent_name>
```

Supported agents:
- `claude`
- `cursor`
- `codex`
- `gemini`
- `antigravity`

## CI/CD Integration

Strictacode provides ready-to-use composite actions and CI templates:

- **[GitHub Actions](ci.md#github-actions)** — composite action with optional thresholds via env vars
- **[GitLab CI](ci.md#gitlab-ci)** — remote include template with the same threshold support
