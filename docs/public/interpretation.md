# Interpreting Metrics

**For:** Technical leads and architects who want to understand the state of a codebase in 5-10 minutes.

**Goal:** Use the output of `strictacode analyze` to identify problem types and prioritize actions.

> Calculation formulas are described in [Metrics](metrics.md). This guide focuses on practical interpretation.

## Example Report

```
$ strictacode analyze ./src --short

Project:
  * lang: python
  * loc: 3095
  * packages: 6
  * modules: 20
  * classes: 34
  * methods: 148
  * functions: 36
  * status:
    - name: healthy
    - score: 18
  * overengineering_pressure:
    - score: 8
  * refactoring_pressure:
    - score: 34
  * complexity:
    - score: 237
    - density: 7.66
```

## Quick Diagnosis: State Table

| Zone                | RP    | OP    | What it means                            | Priority     |
|---------------------|-------|-------|------------------------------------------|--------------|
| 🟢 Healthy          | 0-40  | 0-40  | Code is in good shape                    | Monitoring   |
| 🟡 Spaghetti        | 60+   | 0-40  | Dirty code with no abstractions          | High         |
| 🟡 Overengineering  | 0-40  | 60+   | Abstract but clean                       | Medium       |
| 🟠 Moderate         | 40-60 | 40-60 | Issues present, but balanced             | Planned      |
| 🔴 Crisis           | 60+   | 60+   | Both dirty and abstract                  | Critical     |

**Key indicator:** the difference between RP and OP (`diff = |RP - OP|`):

- `diff <= 30` — balanced project
- `diff > 40` — imbalance, analysis required
- `diff > 50` — severe imbalance, critical issue

## Diagnostic Cheat Sheet

### Step 1: Evaluate the Project Score

```
strictacode analyze <path> --short
```

| Score  | Action                                  |
|--------|-----------------------------------------|
| 0-20   | Everything is fine, move to monitoring  |
| 21-40  | Issues exist, worth addressing          |
| 41-60  | Attention needed, refactoring required  |
| 61-100 | Critical, act immediately               |

### Step 2: Identify the Problem Type

Calculate `diff = |RP - OP|`:

| Diff              | Type            | Follow scenario   |
|-------------------|-----------------|-------------------|
| <= 30 and both < 40 | Healthy        | Scenario 4        |
| <= 30 and one >= 40 | Moderate       | Below             |
| <= 30 and both >= 60 | Crisis        | Scenario 3        |
| > 30 and RP > OP    | Spaghetti     | Scenario 1        |
| > 30 and OP > RP    | Overengineering | Scenario 2      |

### Scenario 5: Moderate (40-60, balanced)

**Example report:**

```
Project:
  * status:
    - name: warning
    - score: 48
  * overengineering_pressure:
    - score: 45
  * refactoring_pressure:
    - score: 52
  * complexity:
    - density: 22.3
```

When both RP and OP are in the 40-60 range and the difference is small (<= 30):

- **What it means:** The code is not in critical condition, but it needs attention. There is both complexity and abstractions in moderate amounts.
- **What to do:**
  1. Run `--details` and find the top 5 most problematic spots
  2. Focus on reducing either RP or OP — do not try to fix both at once
  3. Set a goal: bring the higher metric below 40 within 2-3 sprints

### Step 3: Find Pain Points

```bash
strictacode analyze ./src --details
```

Look for the following in the report:

| Problem             | Look at                                         | Threshold |
|---------------------|-------------------------------------------------|-----------|
| Complex functions   | `Functions` -> `complexity.total`               | > 30      |
| Overloaded classes  | `Classes` -> `overengineering_pressure.score`   | > 70      |
| Dense modules       | `Modules` -> `complexity.density`               | > 50      |

### Step 4: Prioritize Fixes

Order of action:

1. **First** — functions with `complexity > 40` (blocking progress)
2. **Then** — classes with `score > 70` (slowing down development)
3. **After that** — modules with `density > 50` (hurting readability)

## Scenario 1: Spaghetti Code (RP >> OP)

### Example Report

```
$ strictacode analyze ./legacy-module --short

Project:
  * loc: 2840
  * status:
    - name: warning
    - score: 58
  * overengineering_pressure:
    - score: 18
  * refactoring_pressure:
    - score: 72
    - stat(modules):
      + max: 24
      + p90: 16
  * complexity:
    - density: 42.5
    - stat(modules):
      + max: 52
      + p90: 30
```

### Typical Indicators

```
RP:  60-100  (high)
OP:  0-40    (low)
Diff: > 40   (RP significantly higher than OP)
```

### What It Means

The code is "dirty" — lots of branching, high cyclomatic complexity, but the architecture is simple with no unnecessary abstractions.

This is **acute pain**: developers feel it every day. Changes are hard to make, and the risk of bugs is high.

### Where to Look

```bash
strictacode analyze ./legacy-module --details
```

Check the report for:

**Modules with high density:**

```
Modules:
  * order_processor.py:
    - complexity:
      + density: 68.2
      + stat(classes+functions):
        - max: 47
        - p90: 38
```

**Functions with high complexity:**

```
Functions:
  * process_order:
    - file: order_processor.py
    - complexity:
      + total: 47
      + density: 55.0
```

### What to Do

**Priority: high**

1. **Start with the top 5 most complex functions** — 80% of the effect from 20% of the code
2. **Refactoring techniques:**
   - Extract Method — break up large functions
   - Simplify Conditional — flatten nested if/else
   - Decompose Conditional — extract complex conditions
3. **In parallel:** add tests for problematic areas before refactoring

### Red Flags

| Indicator         | Threshold | What It Means                                  |
|-------------------|-----------|-------------------------------------------------|
| `max_complexity`  | > 40      | The function is nearly impossible to change safely |
| `p90_complexity`  | > 25      | The problem is systemic, not localized          |
| `density`         | > 75      | Spaghetti code, a rewrite is needed             |

## Scenario 2: Overengineering (OP >> RP)

### Example Report

```
$ strictacode analyze ./enterprise-core --short

Project:
  * loc: 12400
  * status:
    - name: warning
    - score: 47
  * overengineering_pressure:
    - score: 71
    - stat(modules):
      + avg: 45
      + max: 89
      + p90: 78
  * refactoring_pressure:
    - score: 18
  * complexity:
    - density: 8.2
```

### Typical Indicators

```
RP:  0-40    (low)
OP:  60-100  (high)
Diff: > 40   (OP significantly higher than RP)
```

### What It Means

The code is clean (few branches), but the architecture is overloaded with abstractions, connections, and layers.

This is **chronic pain**: the code works, but it is hard to understand. New developers take a long time to get up to speed. Simple tasks require changes in many places.

### Where to Look

```bash
strictacode analyze ./enterprise-core --details
```

Check the report for:

**Classes with high overengineering_pressure:**

```
Classes:
  * AbstractFactoryManager:
    - overengineering_pressure:
      + score: 89
  * BaseRepository:
    - overengineering_pressure:
      + score: 76
```

**Modules with high avg score:**

```
Modules:
  * factory.py:
    - overengineering_pressure:
      + score: 78
      + stat(classes):
        - avg: 45
        - p90: 72
```

### What to Do

**Priority: medium** (does not block progress, but slows it down)

1. **Simplify key abstractions:**
   - Remove unused layers
   - Merge similar interfaces
   - Drop "just in case" abstractions
2. **Reduce coupling:**
   - Break circular dependencies
   - Introduce dependency injection instead of tight coupling
3. **Document the architecture:** if an abstraction is needed, explain why

### Red Flags

| Indicator         | Threshold | What It Means                            |
|-------------------|-----------|-------------------------------------------|
| `coupling`        | > 4       | Too many connections between classes      |
| `avg_class_score` | > 70      | Classes are overloaded with dependencies  |
| `depth`           | > 8       | Dependency chains are too deep            |

## Scenario 3: Crisis Project (RP ≈ OP >> 0)

### Example Report

```
$ strictacode analyze ./monolith --short

Project:
  * loc: 48500
  * status:
    - name: critical
    - score: 78
  * overengineering_pressure:
    - score: 72
    - stat(modules):
      + avg: 52
      + max: 94
      + p90: 81
  * refactoring_pressure:
    - score: 68
    - stat(modules):
      + avg: 45
      + max: 67
      + p90: 58
  * complexity:
    - density: 35.2
```

### Typical Indicators

```
RP:  60-100  (high)
OP:  60-100  (high)
Diff: <= 30   (balanced, but both high)
```

### What It Means

The worst-case scenario: the code is both dirty and abstract at the same time.

This typically happens in "mature" projects that:

- Started as a prototype/spaghetti codebase
- Accumulated layers of abstraction "for good measure"
- Never went through systematic refactoring

### What to Do

**Priority: critical**

1. **Do not try to fix everything at once** — the project will collapse
2. **Strategy:**
   - Identify 2-3 critical modules (by business importance)
   - Isolate them from the rest of the code (interfaces, adapters)
   - Rewrite these modules from scratch
3. **For everything else:** gradually reduce RP through local refactoring

### Action Plan

| Phase | What to Do                                  | Success Metric                   |
|-------|---------------------------------------------|----------------------------------|
| 1     | Isolate critical modules                    | Clear boundaries                 |
| 2     | Rewrite critical modules                    | RP < 40 in new modules           |
| 3     | Gradual refactoring of the rest             | RP decreases by 10 per sprint    |

## Scenario 4: Healthy Project (baseline)

### Example Report

```
$ strictacode analyze ./clean-service --short

Project:
  * loc: 1520
  * status:
    - name: healthy
    - score: 12
  * overengineering_pressure:
    - score: 8
    - stat(modules):
      + avg: 3
      + max: 9
      + p90: 7
  * refactoring_pressure:
    - score: 14
    - stat(modules):
      + avg: 6
      + max: 18
      + p90: 12
  * complexity:
    - density: 6.8
```

### Typical Indicators

```
RP:  0-40    (low)
OP:  0-40    (low)
Diff: <= 30   (balanced)
```

### What It Means

The code is in good shape. You can focus on features.

### What to Do

**Priority: monitoring**

1. **Run the analysis regularly** (CI/CD or weekly)
2. **Watch the trends:** rising metrics are an early warning sign
3. **Set thresholds:** trigger an alarm when RP > 40 or OP > 40

### Preventing Degradation

| Practice                              | How It Helps                                    |
|---------------------------------------|-------------------------------------------------|
| Code review with complexity checks    | Catches complex functions before merge          |
| Linters with thresholds               | Blocks functions with complexity > 20           |
| Architecture reviews                  | Catches overengineering at an early stage       |

## Summary

| If...                       | Then...                                          |
|-----------------------------|--------------------------------------------------|
| RP is high, OP is low       | Spaghetti — clean up the functions               |
| OP is high, RP is low       | Overengineering — simplify the architecture      |
| Both are high               | Crisis — isolate and rewrite                     |
| Both are low                | Everything is fine — keep monitoring             |
