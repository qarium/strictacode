"""
# Code Quality Analyzer

## Overview

AI agent skill for deep code quality analysis using strictacode. The skill:

1. **Reads configuration** — checks project config, understands settings
2. **Runs analysis** — executes strictacode for the project
3. **Interprets metrics** — determines project type and problem areas
4. **Finds hotspots** — identifies problematic files/functions with iterative expansion
5. **Reads code** — directly analyzes discovered problem areas (max 7 files)
6. **Creates plan** — produces prioritized improvement list

Use this skill when starting work with a new project, planning refactoring, or assessing technical debt.

---

## When to Use

- Starting work with a new or legacy project — understand codebase state
- Planning refactoring — identify where maximum pain comes from minimal effort
- Assessing technical debt before important decisions — quantify "bad code"
- On user request — any time diagnostics are needed

---

## Prerequisites

1. **strictacode installed** — check via `pip show strictacode`
2. **Project path specified** — if not, use current directory

If not installed: `pip install strictacode`

---

## Steps

### Step 1: Read Configuration

Check for configuration file in project root: `.strictacode.yml`, `.strictacode.yaml`, or `.strictacode.json`. If present, read it.

**Default top values** (when not configured):
| Category   | Default |
|------------|---------|
| packages   | 5       |
| modules    | 10      |
| classes    | 20      |
| methods    | 25      |
| functions  | 25      |

**Configuration options:**
- `lang` — project language (`python`, `golang`, `javascript`)
- `loader.exclude` — paths and directories to exclude from analysis
- `reporter.top.*` — number of top elements per category

**Rules:**
- DO read and account for configuration when analyzing the report
- DO suggest excluding directories via `loader.exclude` if they distort metrics (vendor, generated code, mocks, migrations)
- DO NOT create or modify configuration files — only suggest changes to the user
- DO NOT suggest changing `reporter.top.*` values — this is user's decision

### Step 2: Run Analysis

strictacode automatically picks up config from project root. No need to pass config values via CLI flags.

```bash
strictacode analyze <path> --details --format json
```

Flags:
- `--details` — get metrics at module, class, function level
- `--format json` — structured output for parsing

If `loader.exclude` is configured and relevant to analysis, note it in the report.

### Step 3: Interpret General Metrics

#### 3.1 Evaluate Project Score

| Score  | Status    | Action                          |
|--------|-----------|---------------------------------|
| 0-20   | healthy   | All good, proceed to monitoring |
| 21-40  | normal    | Issues exist, should address    |
| 41-60  | warning   | Attention needed                |
| 61-80  | critical  | Refactoring is priority         |
| 81-100 | emergency | Critical, act immediately       |

#### 3.2 Determine Project Type

Calculate: `diff = |RP - OP|`

| Diff    | RP    | OP    | Type            | What it means                       | What to do                                     |
|---------|-------|-------|-----------------|-------------------------------------|------------------------------------------------|
| ≤ 30    | 0-40  | 0-40  | Healthy         | Code is in good condition           | Monitor regularly, set thresholds               |
| ≤ 30    | 40-60 | 40-60 | Moderate        | Both metrics elevated               | Focus on reducing one metric at a time          |
| ≤ 30    | 60+   | 60+   | Crisis          | Both high and balanced              | Isolate critical modules, rewrite from scratch  |
| > 30    | 60+   | 0-40  | Spaghetti       | Dirty code, high complexity         | Refactor top complex functions, extract methods |
| > 30    | 0-40  | 60+   | Overengineering | Excessive abstractions              | Remove unused layers, reduce coupling           |

**Key diff indicator:**
- `diff ≤ 30` — balanced project
- `diff > 40` — imbalance, deeper analysis needed
- `diff > 50` — severe imbalance, critical problem

#### 3.3 Explain Metric Origins

When OP or RP is high, ALWAYS explain it through available statistics from the report.

**For OP (overengineering_pressure):**
Use `stat(modules)` from package level:
- `max` — most overengineered module in package (identify by reading it)
- `p90` — 90th percentile (if high → problem is systemic)
- `avg` — average across modules

**For RP (refactoring_pressure):**
Use `stat(modules)` from project/package level:
- `max` — module with highest complexity
- `p90` — if > 25, problem is systemic
- Also check `complexity.density` and `complexity.stat.max` for function-level detail

**Output format:**
```
<package> — OP=<value> breakdown:
- stat(modules): avg=<X>, max=<Y>, p90=<Z>
- Top contributor (max=<Y>): <module_name>
- Systemic assessment: p90=<Z> → <systemic/local> problem
```

### Step 4: Identify Hotspots

Extract elements from detailed report by thresholds:

| Type     | Metric                           | Threshold | Meaning                              |
|----------|----------------------------------|-----------|--------------------------------------|
| Functions| `complexity.total`               | > 30      | Function hard to change safely       |
| Functions| `complexity.total`               | > 40      | Almost impossible to change          |
| Classes  | `overengineering_pressure.score` | > 70      | Class oversaturated with dependencies|
| Modules  | `complexity.density`             | > 50      | Spaghetti code in module             |
| Modules  | `complexity.density`             | > 75      | Rework required                      |

Also use `status.name`:
- `"critical"` — requires immediate attention
- `"warning"` — requires attention
- `"normal"` / `"healthy"` — acceptable

#### Analyze Statistics

Use `stat(modules)` and `stat(classes+functions)`:
- **max** — most problematic element
- **p90** — 90th percentile (if high — problem is systemic)
- **avg** — project average

**Red flags:**

| Indicator        | Threshold | Meaning                                    |
|------------------|-----------|--------------------------------------------|
| `max_complexity` | > 40      | Function almost impossible to change safely|
| `p90_complexity`  | > 25      | Problem is systemic, not local            |
| `density`        | > 75      | Spaghetti code, rework required           |

> Note: `coupling` and `depth` are NOT available in JSON report. They can only be assessed via direct code reading in Step 5.

#### Prioritization Rules

| Sign                                    | Priority |
|-----------------------------------------|----------|
| complexity > 40 in function             | P0       |
| RP > 80 in critical module (core, api)  | P0       |
| OP > 80 in any part of project          | P0       |
| p90 > 25 (systemic problem)             | P0       |
| RP 60-80 in multiple modules            | P1       |
| OP 60-80 in isolated code               | P1       |
| density > 50 in module                  | P1       |
| Single functions with complexity 20-30  | P2       |

Include 1-2 quick wins (P2, little effort) alongside main problems (P0-P1).

#### Iterative Top Expansion

Only applies when `--details` flag is used (classes/methods/functions data required).

Check the **tail** of each top category (last 2-3 elements). If boundary elements have score > 40 (warning/critical), expand the top and re-run to capture potentially missed problem areas.

**Algorithm:**
1. For each category (packages, modules, classes, methods, functions), check the last 2-3 elements in the top
2. If any boundary element has score > 40 → increase `--top-*` for that category by 50% and re-run
3. Use the expanded run as the source of truth for that category
4. Max 2 iterations

```bash
# Initial run (default top-modules = 10)
strictacode analyze <path> --details --format json

# Boundary element #10 has score 55 → expand
strictacode analyze <path> --details --format json --top-modules 15
```

### Step 5: Analyze Hotspot Code

#### 5.1 Locate Problems Precisely

JSON report provides `file` path but NOT line numbers. You MUST find exact locations.

**To find line numbers:**
1. **Use Grep tool** to find function/class definition:
   - Python: `grep "def function_name"`
   - Go: `grep "func FunctionName"` or `grep "func (.*FunctionName"`
   - JavaScript: `grep "function functionName"`, `grep "const functionName"`, `grep "=>"`
2. **Use Read tool** to read the file and identify line range
3. **Report format:** `file:start-end — description`

**Required for EVERY hotspot:**
- Full file path (relative to project root)
- Line numbers (start-end)
- Function/class name
- Specific problematic lines (if applicable)

#### 5.2 Understand Context

Read at most **7 files** with the highest scores (sorted by score DESC, then complexity.total DESC). For remaining hotspots, describe by metrics only — do not read files.

For each file you read:
1. Understand context — what the function/module does
2. Identify specific problems (long functions, deep nesting, duplication)

### Step 6: Create Improvement Plan

Every recommendation MUST include concrete details. Use report data + file analysis.

**For function refactoring, provide:**
| Field | Source |
|-------|--------|
| Current LOC | Read function code |
| Extract candidates | Identify logical blocks in code |
| Line ranges | From code analysis |
| Effort | `small` (single function) / `medium` (multiple functions) / `large` (package, breaking imports) |

**For package refactoring, provide:**
| Field | Source |
|-------|--------|
| Files to move | Read package directory, identify patterns |
| Destination | Logical grouping |
| File count | From directory listing |
| LOC estimate | `package.loc` / `package.modules` * files_to_move |
| Breaking imports | Grep for package import path |

Form a prioritized list with:
- Priority (P0 — critical, P1 — important, P2 — desirable)
- Specific action with file:line
- Justification (which metrics will be affected)
- Expected effect (concrete numbers when possible)

---

## Output Format

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

### Metric Breakdown (REQUIRED if OP > 40 or RP > 40)

```
## Metric Breakdown

### OP Breakdown (if OP > 40)
| Package | OP  | stat.avg | stat.max | stat.p90 | Assessment |
|---------|-----|----------|----------|----------|------------|
| <name>  | <X> | <Y>      | <Z>      | <W>      | systemic/local |

### RP Breakdown (if RP > 40)
| Module | RP  | stat.avg | stat.max | stat.p90 | density | Problem function |
|--------|-----|----------|----------|----------|---------|------------------|
| <name> | <X> | <Y>      | <Z>      | <W>      | <D>     | <func>:<line>    |
```

### Red Flags (if any)

```
## Red Flags

1. `<file:start-end>` — <function_name>() has complexity <X>
   - Threshold: 40 (almost impossible to change safely)
   - Problem lines: <start>-<end> — <specific issue>
```

### Improvement Plan

```
## Improvement Plan

### P0 — Critical
1. **<Action>**
   - Location: `<file:start-end>`
   - Justification: <why important, which metric>
   - Expected effect: <concrete numbers>
   - Effort: <small | medium | large>
   - Breaking changes: <list files that need updates>

### P1 — Important
...

### P2 — Desirable
...
```

---

## Report Fields Reference

JSON report structure:
- `project` — general project metrics (status, RP, OP, complexity)
- `packages` — package metrics (OP, RP, density, stat)
- `modules` — module metrics (OP, RP, density, stat)
- `classes` — class metrics (OP, complexity, stat)
- `methods` — method metrics (complexity, stat)
- `functions` — function metrics (complexity, stat)

> Note: JSON report does NOT include fan_out/fan_in/depth/centrality. Use code reading to assess these.

---

## Edge Cases

### Empty or New Project

If report contains little data (LOC < 100, modules < 3):
- Inform user: "Project too small for full analysis"
- Offer basic structure recommendations

### All Metrics Normal

If project.status.name = "healthy" and no elements with status.name = "critical" or "warning":
- Confirm healthy project state
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
