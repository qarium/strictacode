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

#### Step 2.3: Explain Metric Origins

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

**Output format for breakdown:**
```
<package> — OP=<value> breakdown:
- stat(modules): avg=<X>, max=<Y>, p90=<Z>
- Top contributor (max=<Y>): <module_name> — read file to understand why
- Systemic assessment: p90=<Z> → <systemic/local> problem
```

**Example:**
```
<package_name> — OP=<value> breakdown:
- stat(modules): avg=<X>, max=<Y>, p90=<Z>
- Top contributor: <module_name> (after reading: <N> types, imported everywhere)
- p90=<Z> → problem is systemic (90% of modules have OP up to <Z>)
- Main driver: many small types with high fan-in (imported by <N>+ modules each)
```

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

#### Step 4.1: Locate Problems Precisely

JSON report provides `file` path but NOT line numbers. You MUST find exact locations.

**To find line numbers:**
1. **Use Grep tool** to find function/class definition:
   - Python: `grep "def function_name"`
   - Go: `grep "func FunctionName"` or `grep "func (.*FunctionName"`
   - JavaScript: `grep "function functionName"\\|grep "const functionName"`
2. **Use Read tool** to read the file and identify line range
3. **Report format:** `file:start-end — description`

**Example workflow:**
```
Problem: <function_name> has complexity 42

1. Grep "func <FunctionName>" → found in <path/to/file>.go
2. Read <file>.go → function spans lines 281-332 (52 lines)
3. Analyze code → switch statement with many cases at lines 285-310
4. Report: <path/to/file>.go:281-332 — <FunctionName>() complexity=42
```

**Required for EVERY hotspot:**
- Full file path (relative to project root)
- Line numbers (start-end)
- Function/class name
- Specific problematic lines (if applicable)

#### Step 4.2: Understand Context

For each hotspot:
1. Read the file with problematic code
2. Understand context — what the function/module does
3. Identify specific problems (long functions, deep nesting, duplication)

### Step 5: Create Improvement Plan

#### Step 5.1: Make Recommendations Actionable

Every recommendation MUST include concrete details. Use report data + file analysis.

**For package refactoring, provide:**
| Field | Source |
|-------|--------|
| Files to move | Read package directory, identify patterns (e.g., `<prefix>_*.go`) |
| Destination | Logical grouping (e.g., `db/drivers/`) |
| File count | From directory listing |
| LOC estimate | `package.loc` / `package.modules` * files_to_move |
| Breaking imports | Grep for package import path |

**Example:**
```
Refactor <package_name>:
- From report: 35 modules, 10,192 LOC

Files to move (after reading directory):
| Pattern          | Destination       | Files | LOC est. |
|------------------|-------------------|-------|----------|
| <prefix1>_*.go   | <new_pkg>/<dir1>/ | 12    | ~3,500   |
| <prefix2>_*.go   | <new_pkg>/<dir2>/ | 8     | ~2,300   |
| <prefix3>_*.go   | <new_pkg>/<dir3>/ | 6     | ~1,700   |

Breaking imports (grep "<package_name>"):
- <service>/<module1>.go:45
- <api>/<module2>.go:12
- <cmd>/<module3>.go:23

Effort: ~4-6 hours (rename imports + run tests)
```

**For function refactoring, provide:**
| Field | Source |
|-------|--------|
| Current LOC | Read function code |
| Extract candidates | Identify logical blocks in code |
| Line ranges | From code analysis |
| Effort estimate | Based on complexity |

**Example:**
```
Split <FunctionName> (<path/to/file>.go:281-332):
- Current: 52 LOC, complexity 42
- Extract: <HelperFunction1>() — lines 285-310 (~25 LOC)
- Extract: <HelperFunction2>() — lines 315-340 (~25 LOC)
- Remaining: ~50 LOC with core business logic
- Effort: ~2-3 hours + tests
```

#### Step 5.2: Prioritize and Format

Form a prioritized list with:
- Priority (P0 — critical, P1 — important, P2 — desirable)
- Specific action with file:line
- Justification (which metrics will be affected)
- Expected effect (concrete numbers when possible)

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

### Metric Breakdown (if OP > 40 or RP > 40)

REQUIRED when any metric is elevated. Use `stat()` data from report.

```
## 📊 Metric Breakdown

### OP Breakdown (if OP > 40)
| Package | OP  | stat.avg | stat.max | stat.p90 | Assessment |
|---------|-----|----------|----------|----------|------------|
| <name>  | <X> | <Y>      | <Z>      | <W>      | systemic/local |

Top contributor: <file> — read analysis shows <reason>

### RP Breakdown (if RP > 40)
| Module | RP  | stat.avg | stat.max | stat.p90 | density | Problem function |
|--------|-----|----------|----------|----------|---------|------------------|
| <name> | <X> | <Y>      | <Z>      | <W>      | <D>     | <func>:<line>    |
```

### Red Flags (if any)

```
## 🚨 Red Flags

1. `<file:start-end>` — <function_name>() has complexity <X>
   - Threshold: 40 (almost impossible to change safely)
   - Problem lines: <start>-<end> — <specific issue>
```

### Pain Points

```
## 🔥 Pain Points

### <file:start-end> — <function/module name>
- **Problem:** <brief description>
- **Metrics:** complexity=<X> (threshold: <Y>), density=<Z>
- **Context:** <what this code does>
- **Specific issues:** <list with line numbers>
```

### Improvement Plan

```
## 📋 Improvement Plan

### P0 — Critical
1. **<Action>**
   - Location: `<file:start-end>`
   - Justification: <why important, which metric>
   - Expected effect: <concrete numbers>
   - Effort: <time estimate>
   - Breaking changes: <list files that need updates>

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
  "name": "<function_name>",
  "file": "<module_name>.py",
  "loc": <N>,
  "status": {"name": "critical", "score": <X>},
  "complexity": {
    "score": <X>,
    "total": <X>,
    "density": <D>
  }
}
```

**Step 1 — Locate:**
```
Grep "def <function_name>" → <module_name>.py:<line>
Read <module_name>.py → function spans lines <start>-<end> (<N> LOC)
```

**Step 2 — Report:**
```
<module_name>.py:<start>-<end> — <function_name>()
- complexity = <X> > 40 → red flag
- density = <D> > 50 → spaghetti code
- Lines <l1>-<l2>: <specific_issue> (main complexity source)
```

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

### OP Breakdown Example

**Report data:**
```json
{
  "packages": [
    {
      "name": "<package_name>",
      "overengineering_pressure": {"score": <value>},
      "complexity": {"density": <X>},
      "loc": <N>,
      "modules": <M>
    }
  ]
}
```

**Note:** JSON report does NOT include fan_out/fan_in/depth/centrality.
Use `stat()` and code analysis to explain.

**Analysis workflow:**
```
1. Report shows: OP=<value>, <N> modules, density=<X> (low = many simple types)
2. Read <package_name> directory → list files
3. Read 2-3 largest files → count structs/types, find import patterns
4. Grep "<package_name>" → count how many files import this package
5. Conclude: high fan_in (types imported everywhere) drives OP
```

**Output:**
```
<package_name> — OP=<value> breakdown:
- stat(modules): avg=<X>, max=<Y>, p90=<Z> (from detailed report)
- Modules: <N> files, <LOC> lines, density=<D> (many simple types)
- Code analysis:
  - <file1>.go: <N1> struct definitions
  - <file2>.go: <N2> struct definitions
  - <file3>.go: <N3> struct definitions
- Import analysis: <package_name> imported by <N>+ files across project
- Main driver: high fan_in (types imported everywhere, not high fan_out)
- p90=<Z> → problem is systemic (90% of modules have OP up to <Z>)
- Recommendation: split by domain (<package>/<domain1>/, <package>/<domain2>/, ...)
```

### Improvement Plan Example

```
### P0 — Critical
1. Split <function_name> into sub-functions
   - Location: `<module_name>.py:<start>-<end>`
   - Justification: complexity <X> > 40, function blocks changes
   - Extract candidates:
     - <helper1>() — lines <l1>-<l2> (~<n1> LOC)
     - <helper2>() — lines <l3>-<l4> (~<n2> LOC)
     - <helper3>() — lines <l5>-<l6> (~<n3> LOC)
   - Expected effect: complexity ~15 per function
   - Effort: ~3 hours + tests
   - Breaking changes: none (internal refactoring)

### P1 — Important
2. Simplify <module_name> module
   - Location: `<module_name>.py`
   - Justification: module RP = <X>, density = <Y> > 50
   - Files affected: <module_name>.py (1 file, <N> LOC)
   - Expected effect: reduce project RP by ~10-15 points
   - Effort: ~4-6 hours

### P2 — Desirable
3. Add tests for <function_name> before refactoring
   - Location: `tests/test_<module_name>.py`
   - Justification: refactoring safety
   - Test cases needed: 5-7 (happy path + edge cases)
   - Effort: ~2 hours
```

### Package Refactoring Example

**Report data:**
```json
{
  "name": "<package_name>",
  "dir": "<package_path>",
  "loc": <N>,
  "modules": <M>,
  "overengineering_pressure": {"score": <value>}
}
```

**Analysis workflow:**
```
1. Read <package_path> directory → list files
2. Identify patterns: <prefix1>_*.go (<N1>), <prefix2>_*.go (<N2>), <prefix3>_*.go (<N3>)
3. Grep "<package_name>" for breaking imports
4. Calculate LOC per pattern
```

**Output:**
```
Refactor <package_name> (OP=<value>):
- Current: <M> modules, <N> LOC

Files to move:
| Pattern           | Destination          | Files | LOC est. |
|-------------------|----------------------|-------|----------|
| <prefix1>_*.go    | <new_pkg>/<subdir1>/ | <N1>  | ~<LOC1>  |
| <prefix2>_*.go    | <new_pkg>/<subdir2>/ | <N2>  | ~<LOC2>  |
| <prefix3>_*.go    | <new_pkg>/<subdir3>/ | <N3>  | ~<LOC3>  |

Breaking imports (grep "<package_name>"):
- <module1>.go:<line1>,<line2>
- <module2>.go:<line1>,<line2>
- <module3>.go:<line1>

Effort: ~4-6 hours (rename imports + run tests)
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
