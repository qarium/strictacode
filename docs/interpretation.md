# Metric Interpretation

This guide explains how to read strictacode results and what each metric means in practice.

## Core Metrics

strictacode produces four key metrics:

| Metric                       | What it measures                                  | Good  | Bad   |
|------------------------------|---------------------------------------------------|-------|-------|
| **Project Score**            | Overall codebase health (0--100, lower is better) | 0--20 | 60+   |
| **Refactoring Pressure (RP)**| How much the code "pressures" the developer       | 0--40 | 60+   |
| **Overengineering Pressure (OP)** | How excessive the architecture is            | 0--40 | 60+   |
| **Complexity Density**       | Concentration of complexity per line of code      | < 20  | > 50  |

---

## Project Score

The project score is a weighted combination of RP, OP, and complexity density, with an additional adjustment for imbalance between RP and OP.

### Score Thresholds

| Score  | Status    | Meaning                                |
|--------|-----------|----------------------------------------|
| 0--20  | healthy   | Code is in good condition              |
| 21--40 | normal    | Issues exist but are manageable        |
| 41--60 | warning   | Attention needed, refactoring required |
| 61--80 | critical  | Refactoring is a priority              |
| 81--100| emergency | Critical state, act immediately        |

---

## Refactoring Pressure (RP)

Measures how difficult it is to change the code without introducing bugs. Based on peak complexity (max and p90) and overall complexity density.

### RP Thresholds

| Score  | Status   | Meaning                              |
|--------|----------|--------------------------------------|
| 0--20  | minimal  | Code is easy to change safely        |
| 21--40 | low      | Light pressure, minor cleanup needed |
| 41--60 | medium   | Noticeable pressure                  |
| 61--80 | high     | Strong pressure, refactor priority   |
| 81--100| extreme  | Critical state, immediate action     |

### What Drives RP

- **Peak pressure (60% weight):** How complex are the most complex functions.
  Non-linear scale: complexity 10 gives ~40%, complexity 25 gives ~85%, complexity 40 gives ~95%.
- **Base pressure (40% weight):** Overall complexity density across the codebase.
  Scales with project size -- larger projects naturally have lower density, so a scaling factor compensates.

### How to Improve

- Extract methods from long, complex functions
- Reduce nesting depth
- Eliminate duplicated logic
- Simplify conditional branches

---

## Overengineering Pressure (OP)

Measures how excessive the architecture is -- coupling, abstraction depth, and unnecessary indirection. Based on dependency graph analysis (fan-out, fan-in, depth, centrality).

### OP Thresholds

| Score  | Status           | Meaning                          |
|--------|------------------|----------------------------------|
| 0--20  | simple           | Architecture is straightforward  |
| 21--40 | moderate         | Some unnecessary complexity      |
| 41--60 | complex          | Approaching complexity threshold |
| 61--80 | overengineered   | Excessive abstraction depth      |
| 81--100| bloated          | Severely overengineered          |

### What Drives OP

- **Coupling (40% weight):** Average number of edges per node in the dependency graph.
- **Class-level scores (60% weight):** Each class is scored on:
  - Fan-out (35%): How many other classes this one depends on
  - Fan-in (25%): How many other classes depend on this one
  - Depth (25%): Maximum shortest-path distance to any other node
  - Centrality (15%): How often this node appears on shortest paths

### How to Improve

- Remove unused layers of abstraction
- Reduce coupling between modules
- Split large packages by domain
- Consolidate types that are imported everywhere

---

## Complexity Density

Concentration of complexity per line of code. Calculated as `(complexity_score / LOC) * 100`.

### Density Thresholds

| Density | Status        | Meaning                                    |
|---------|---------------|--------------------------------------------|
| 0--10   | clean         | Very low complexity concentration           |
| 11--20  | good          | Healthy complexity level                    |
| 21--30  | moderate      | Complexity requires attention               |
| 31--50  | dirty         | High concentration of complexity            |
| 51--75  | very-dirty    | Very high concentration, spaghetti territory|
| 76--100 | spaghetti     | Severely tangled code                      |
| > 100   | unreadable    | Code is practically impossible to follow    |

---

## Diagnosing Your Project

The key to interpreting strictacode results is comparing **Refactoring Pressure** and **Overengineering Pressure**. Calculate the difference:

```
diff = |RP - OP|
```

### Project Types

| Diff | RP    | OP    | Type            | What it means                       | What to do                                     |
|------|-------|-------|-----------------|-------------------------------------|------------------------------------------------|
| <= 30| 0--40 | 0--40 | Healthy         | Code is in good condition           | Monitor regularly, set thresholds               |
| <= 30| 40--60| 40--60| Moderate        | Both metrics elevated               | Focus on reducing one metric at a time          |
| <= 30| 60+   | 60+   | Crisis          | Both high and balanced              | Isolate critical modules, rewrite from scratch  |
| > 30 | 60+   | 0--40 | Spaghetti       | Dirty code, high complexity         | Refactor top complex functions, extract methods |
| > 30 | 0--40 | 60+   | Overengineering | Excessive abstractions              | Remove unused layers, reduce coupling           |

### Diff Indicator

- `diff <= 30` -- balanced project
- `diff > 40` -- imbalance, analysis needed
- `diff > 50` -- severe imbalance, critical problem

### Imbalance Penalty

When RP and OP are severely imbalanced, the project score receives an additional penalty:

- **Spaghetti imbalance (RP >> OP):** Penalized more heavily because it represents acute pain -- code is actively blocking development.
- **Overengineering imbalance (OP >> RP):** Penalized less because it is a chronic problem -- the code works but is harder to maintain than necessary.

---

## Red Flags

Watch for these danger indicators:

| Indicator        | Threshold | Meaning                                      |
|------------------|-----------|----------------------------------------------|
| `max_complexity` | > 40      | Function almost impossible to change safely  |
| `p90_complexity` | > 25      | Problem is systemic, not just local          |
| `density`        | > 75      | Spaghetti code, rework required              |
| RP score         | > 80      | Extreme refactoring pressure                 |
| OP score         | > 80      | Bloated architecture                         |

---

## Using Statistics

Detailed reports include `stat()` fields that help distinguish local from systemic problems:

- **max** -- most problematic element
- **p90** -- 90th percentile. If p90 is high, the problem is systemic (affects most of the codebase)
- **avg** -- average across all elements

### Example Interpretation

```
refactoring_pressure:
  score: 72
  stat(modules):
    avg: 8
    max: 24
    p90: 16
```

- `max = 24` -- one module has high RP
- `p90 = 16` -- problem is not systemic (p90 < 25)
- **Conclusion:** local problem, focus on the worst module

---

## Common Scenarios

### Spaghetti Code (high RP, low OP, diff > 40)

Symptoms:
- RP > 60, OP < 40
- High complexity density
- Functions with complexity > 30

Diagnosis: Code has accumulated complexity without proper abstractions.

Actions:
1. Identify top complex functions (`--details`)
2. Extract helper methods
3. Simplify conditional logic
4. Add tests before refactoring

### Overengineering (high OP, low RP, diff > 40)

Symptoms:
- OP > 60, RP < 40
- Low complexity density (many simple types)
- High coupling between packages

Diagnosis: Architecture is overly complex for the problem it solves.

Actions:
1. Review dependency graph for unnecessary connections
2. Consolidate types imported everywhere
3. Remove unused abstraction layers
4. Consider merging small packages

### Crisis (both RP and OP high)

Symptoms:
- RP > 60 and OP > 60
- Balanced (diff <= 30) or imbalanced

Diagnosis: The worst case -- code is both complex and overarchitected.

Actions:
1. Do not try to fix everything at once
2. Isolate critical modules
3. Rewrite the worst modules from scratch
4. Gradual refactoring for the rest

### Healthy (both RP and OP low)

Symptoms:
- RP < 40 and OP < 40
- Project score < 20

Diagnosis: Code is in good shape.

Actions:
- Continue monitoring
- Set quality thresholds in CI/CD
- Maintain code review practices
