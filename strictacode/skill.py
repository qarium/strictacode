"""
# Code Quality Analyzer

## Overview

AI agent skill for deep code quality analysis using strictacode. The skill:

1. **Runs analysis** — executes strictacode for the project
2. **Interprets metrics** — understands RP, OP, Complexity Density and their combinations
3. **Finds hotspots** — identifies problematic files/functions by detailed metrics
4. **Reads code** — directly analyzes discovered problem areas
5. **Creates plan** — produces prioritized improvement list with concrete steps

Use this skill when starting work with a new project, planning refactoring, or assessing technical debt.

---

## When to Use

Use this skill when:

- Starting work with a new or legacy project — understand codebase state
- Planning refactoring — identify where maximum pain comes from minimal effort
- Conducting sprint retrospective — objective quality data
- Assessing technical debt before important decisions — quantify "bad code"
- Onboarding new developers — show where complexity is concentrated
- Before major changes — understand regression risks
- On user request — any time diagnostics are needed

---

## Prerequisites

Before running analysis, verify:

1. **strictacode installed** — check via `pip show strictacode`
2. **Project path specified** — if not, use current directory

If strictacode is not installed:
```
pip install strictacode
```

---

## Steps

### Step 1: Run Analysis

Execute strictacode command:
```bash
strictacode analyze <path> --details --format json
```

Flags:
- `--details` — get metrics at module, class, function level
- `--format json` — structured output for parsing

### Step 2: Interpret General Metrics

#### Step 2.1: Evaluate Project Score

| Score  | Status    | Action                              |
|--------|-----------|-------------------------------------|
| 0-20   | healthy   | All good, proceed to monitoring     |
| 21-40  | normal    | Issues exist, should address        |
| 41-60  | warning   | Attention needed, refactoring required |
| 61-80  | critical  | Refactoring is priority             |
| 81-100 | emergency | Critical, act immediately           |

#### Step 2.2: Calculate diff and Determine Problem Type

Calculate: `diff = |RP - OP|`

| Diff    | RP    | OP    | Type           | Action                      |
|---------|-------|-------|----------------|-----------------------------|
| ≤ 30    | 0-40  | 0-40  | Healthy        | Monitoring                  |
| ≤ 30    | 40-60 | 40-60 | Moderate       | Planned refactoring         |
| ≤ 30    | 60+   | 60+   | Crisis         | Isolate and rewrite         |
| > 30    | 60+   | 0-40  | Spaghetti      | Function refactoring        |
| > 30    | 0-40  | 60+   | Overengineering| Simplify architecture       |

**Key diff indicator:**
- `diff ≤ 30` — balanced project
- `diff > 40` — imbalance, analysis needed
- `diff > 50` — severe imbalance, critical problem

### Step 3: Identify Hotspots

Extract elements from detailed report by thresholds:

| Type     | Metric                              | Threshold | Meaning                              |
|----------|-------------------------------------|-----------|--------------------------------------|
| Functions| `complexity.total`                  | > 30      | Function hard to change safely       |
| Functions| `complexity.total`                  | > 40      | Almost impossible to change          |
| Classes  | `overengineering_pressure.score`    | > 70      | Class oversaturated with dependencies|
| Modules  | `complexity.density`                | > 50      | Spaghetti code in module             |
| Modules  | `complexity.density`                | > 75      | Rework required                      |

Also use `status.name`:
- `"critical"` — requires immediate attention
- `"warning"` — requires attention
- `"normal"` / `"healthy"` — acceptable

#### Analyze Statistics (stat fields)

Use `stat(modules)` and `stat(classes+functions)`:
- **max** — most problematic element
- **p90** — 90th percentile (if p90 is high — problem is systemic)
- **avg** — project average

**Red flags:**

| Indicator        | Threshold | Meaning                                    |
|------------------|-----------|--------------------------------------------|
| `max_complexity` | > 40      | Function almost impossible to change safely|
| `p90_complexity`  | > 25      | Problem is systemic, not local            |
| `density`        | > 75      | Spaghetti code, rework required           |
| `coupling`       | > 4       | Too many connections between classes      |
| `depth`          | > 8       | Dependency chains too deep                |

### Step 4: Analyze Hotspot Code

For each hotspot:
1. Read the file with problematic code
2. Understand context — what the function/module does
3. Identify specific problems (long functions, deep nesting, duplication)

### Step 5: Create Improvement Plan

Form a prioritized list with:
- Priority (P0 — critical, P1 — important, P2 — desirable)
- Specific action
- Justification (which metrics will be affected)
- Expected effect

---

## Decision Logic

### Action Scenarios by Problem Type

#### Scenario 1: Spaghetti Code (RP >> OP, diff > 40)

**What it is:** Dirty code — many branches, high complexity, but without excessive abstractions. Acute pain: developers feel it every day.

**What to do:**
1. Start with top 5 most complex functions (80% effect from 20% code)
2. Refactoring techniques: Extract Method, Simplify Conditional, Decompose Conditional
3. Add tests for problem areas before refactoring

#### Scenario 2: Overengineering (OP >> RP, diff > 40)

**What it is:** Clean code (few branches), but architecture is oversaturated with abstractions. Chronic pain: hard to understand, simple tasks require changes in many places.

**What to do:**
1. Simplify key abstractions — remove unused layers
2. Reduce coupling — break circular dependencies
3. Document architecture — if abstraction is needed, explain why

#### Scenario 3: Crisis (RP ≥ 60 and OP ≥ 60, diff ≤ 30)

**What it is:** Worst case scenario — code is both dirty and abstract simultaneously.

**What to do:**
1. Don't try to fix everything at once — project will fall apart
2. Identify 2-3 critical modules (by business importance)
3. Isolate them from the rest of the code (interfaces, adapters)
4. Rewrite these modules from scratch

#### Scenario 4: Healthy (RP < 40 and OP < 40)

**What it is:** Code is in good condition. Can focus on features.

**What to do:**
1. Run analysis regularly (CI/CD or weekly)
2. Monitor trends — growing metrics = early warning
3. Set thresholds: alarm when RP > 40 or OP > 40

#### Scenario 5: Moderate (RP 40-60 and OP 40-60, diff ≤ 30)

**What it is:** Code is not critical but needs attention. Both complexity and abstractions exist in moderate amounts.

**What to do:**
1. Find top 5 problem areas via `--details`
2. Focus on reducing either RP or OP — don't try to fix both at once
3. Set goal: reduce maximum metric to < 40 in 2-3 sprints

### Prioritization Rules

| Sign                                         | Priority |
|----------------------------------------------|----------|
| complexity > 40 in function                  | P0       |
| RP > 80 in critical module (core, api)       | P0       |
| OP > 80 in any part of project               | P0       |
| p90 > 25 (systemic problem)                  | P0       |
| RP 60-80 in multiple modules                 | P1       |
| OP 60-80 in isolated code                    | P1       |
| density > 50 in module                       | P1       |
| Single functions with complexity 20-30       | P2       |
| Cosmetic issues (names, formatting)          | P2       |

### Balance Quick Wins and Deep Changes

The plan should include:
- 1-2 quick wins (P2, little effort) — for quick progress
- Main problems (P0-P1) — systemic improvements

---

## Output Format

Present analysis results in the following format:

### Project Summary

```
## Project Analysis: <name>

**Overall State:** <Spaghetti | Overengineering | Crisis | Moderate | Healthy>
**Project Score:** <value> (<status: healthy/normal/warning/critical/emergency>)
**Refactoring Pressure:** <value>
**Overengineering Pressure:** <value>
**Diff (|RP - OP|):** <value> (<balanced/imbalance/critical imbalance>)
**Complexity Density:** <value>
```

### Red Flags (if any)

```
## 🚨 Red Flags

- max_complexity = <X> in <function> — <why critical>
- p90_complexity = <X> — <systemic/local problem>
- density = <X> in <module> — <rework required>
```

### Pain Points

```
## Pain Points

### <File/Module 1>
- **Problem:** <brief description>
- **Metrics:** complexity=<X> (threshold: <Y>), density=<Z>
- **Context:** <what this code does>

### <File/Module 2>
...
```

### Improvement Plan

```
## Improvement Plan

### P0 — Critical
1. **<Action>**
   - File: <path>
   - Justification: <why important>
   - Expected effect: <which metrics affected>

### P1 — Important
...

### P2 — Desirable
...
```

---

## Examples

### Report Analysis Example

**Input:** JSON report from strictacode with fields:
- `project` — general project metrics
- `packages` — package metrics
- `modules` — module metrics
- `classes` — class metrics
- `methods` — method metrics
- `functions` — function metrics

### Interpretation Example

```json
{
  "project": {
    "status": {"name": "warning", "score": 58},
    "refactoring_pressure": {"score": 72},
    "overengineering_pressure": {"score": 8},
    "complexity": {"density": 42.5}
  }
}
```

**Calculation:** diff = |72 - 8| = 64 > 50 → critical imbalance

**Diagnosis:** Spaghetti code (RP high, OP low, diff > 40)

### Function Hotspot Example

```json
{
  "name": "process_order",
  "file": "order_service.py",
  "loc": 85,
  "status": {"name": "critical", "score": 78},
  "complexity": {
    "score": 45,
    "total": 45,
    "density": 52.9
  }
}
```

**Pain point:** `order_service.py:process_order`
- complexity = 45 > 40 → red flag: function almost impossible to change safely
- density = 52.9 > 50 → spaghetti code

### Statistics Analysis Example

```json
{
  "refactoring_pressure": {
    "score": 72,
    "stat(modules)": {
      "avg": 8,
      "max": 24,
      "p90": 16
    }
  }
}
```

**Interpretation:**
- max = 24 → module with high RP exists
- p90 = 16 → problem not systemic (p90 < 25)
- Conclusion: local problem, focus on one module

### Improvement Plan Example

```
### P0 — Critical
1. Split process_order into sub-functions
   - File: order_service.py
   - Justification: complexity 45 > 40, function blocks changes
   - Effect: reduce complexity to ~15, improve testability

### P1 — Important
2. Simplify order_service module
   - File: order_service.py
   - Justification: module RP = 24, density = 52.9 > 50
   - Effect: reduce overall project RP by ~10-15 points

### P2 — Desirable
3. Add tests for process_order before refactoring
   - File: tests/test_order_service.py
   - Justification: refactoring safety
   - Effect: reduce regression risk
```

---

## Edge Cases

### Empty or New Project

If report contains little data (LOC < 100, modules < 3):
- Inform user: "Project too small for full analysis"
- Offer basic structure recommendations

### All Metrics Normal

If project.status.name = "healthy" and no elements with status.name = "critical" or "warning":
- Confirm healthy project state
- Point out best practices for maintaining quality (code review with complexity checks, linters with thresholds)
- Recommend regular monitoring
- Don't suggest excessive improvements

### Contradictory Metrics

If both RP and OP are high (crisis) but project is small:
- Note the anomaly
- Suggest understanding architecture first
- Recommend isolating problem areas before refactoring

### No Problem Elements

If no functions/classes with bad metrics but overall metrics are bad:
- Problem is in complexity distribution
- Analyze statistics (stat fields: avg, p90, max)
- Focus on redistributing load between modules

### diff ≤ 30 but Both Metrics High

If diff ≤ 30 (balanced) but RP ≥ 60 and OP ≥ 60:
- This is "Crisis" scenario — worst case
- Don't try to fix everything at once
- Strategy: isolation → rewrite critical modules → gradual refactoring
"""

import os
import typing as t

AGENT_PATHS = {
    "claude": "~/.claude/skills/",
    "cursor": "~/.agents/skills/",
    "codex": "~/.codex/skills/",
    "gemini": "~/.agents/skills/",
    "antigravity": "~/.agents/skills/",
}

__all__ = ["install"]


HEADER: t.Final[str] = """---
name: {skill_name}
description: Deep code quality analysis using strictacode
---

"""


def _get_skill_path(agent: str, skill_name: str) -> str:
    if agent not in AGENT_PATHS:
        raise ValueError(f"Unknown agent: {agent}. Supported: {list(AGENT_PATHS.keys())}")

    # Validate skill_name to prevent path traversal
    if "/" in skill_name or "\\" in skill_name or skill_name in (".", ".."):
        raise ValueError(f"Invalid skill name: {skill_name}")

    base_path = os.path.expanduser(AGENT_PATHS[agent])
    return os.path.join(base_path, skill_name, "SKILL.md")


def install(skill_name: str, agent: str) -> str:
    file_path = _get_skill_path(agent, skill_name)

    dir_path = os.path.dirname(file_path)
    os.makedirs(dir_path, exist_ok=True)

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(HEADER.format(skill_name=skill_name))
        f.write(__doc__)

    return file_path
