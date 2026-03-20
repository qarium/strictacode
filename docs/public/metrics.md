# Code Quality Metrics

This documentation describes the metrics that strictacode uses to evaluate the state of a codebase.

## Quick Reference

### Project Score

**What it is:** Overall project health score from 0 to 100.

| Score  | Status      | What to do                      |
|--------|-------------|---------------------------------|
| 0-20   | `healthy`   | Code is in excellent shape      |
| 21-40  | `normal`    | There are issues, but workable  |
| 41-60  | `warning`   | Worth paying attention to       |
| 61-80  | `critical`  | Refactoring is a priority       |
| 81-100 | `emergency` | Code is blocking work           |

### Refactoring Pressure (RP)

**What it is:** Refactoring pressure from 0 to 100.

| RP     | What to do                        |
|--------|-----------------------------------|
| 0-20   | Everything is fine, keep it up    |
| 21-40  | There are issues, but not urgent  |
| 41-60  | Should address soon               |
| 61-80  | Refactoring is a priority         |
| 81-100 | Should have been done yesterday   |

### Overengineering Pressure (OP)

**What it is:** Excessive architectural complexity indicator from 0 to 100.

| OP     | What to do                              |
|--------|-----------------------------------------|
| 0-20   | Simple architecture, easy to understand |
| 21-40  | Moderate complexity, acceptable         |
| 41-60  | Too many abstractions, consider simplifying |
| 61-80  | Overengineering, refactoring needed     |
| 81-100 | Chaos, needs a complete overhaul        |

### Complexity Density

**What it is:** Complexity density, how "packed" the code is.

| Density | What kind of code                   |
|---------|-------------------------------------|
| 0-20    | Clean, easy to read                 |
| 21-50   | Somewhat dirty, but tolerable       |
| 51-100  | Spaghetti, hard to change           |
| 100+    | Unreadable, refactoring required    |

## Project Score

### What it measures

Project Score is an aggregated project health metric that combines RP, OP, and Complexity Density. The formula takes into account not only the metric values themselves, but also their relationship to each other.

### Score Scale

| Score  | Status      | Interpretation       | Action                    |
|--------|-------------|----------------------|---------------------------|
| 0-20   | `healthy`   | Code is healthy      | Maintain current level    |
| 21-40  | `normal`    | Normal state         | Routine monitoring        |
| 41-60  | `warning`   | There are issues     | Pay attention             |
| 61-80  | `critical`  | Critical state       | Refactoring is a priority |
| 81-100 | `emergency` | Emergency situation  | Immediate action required |

### How it is calculated

**Base formula:**

```
base_score = 0.4 × RP + 0.4 × OP + 0.2 × density
```

**Imbalance check:**

A strong imbalance between RP and OP indicates a problem:
- **RP >> OP** -- spaghetti code: dirty but without abstractions (an acute problem)
- **OP >> RP** -- overengineering: abstract but clean (a chronic problem)

A hybrid approach is used to account for imbalance:

```
diff = |RP - OP|
extremum = max(RP, OP)

if diff <= 30:
    penalty = 0  # No imbalance

elif extremum >= 35:
    # High extremum — additive penalty
    penalty = calculate_penalty(diff, direction)

else:
    # Low extremum — multiplier
    score = base_score × multiplier
```

**Penalty scales:**

| Diff  | Spaghetti (RP >> OP) | Overengineering (OP >> RP) |
|-------|----------------------|----------------------------|
| > 50  | +25 / ×1.8           | +12 / ×1.3                 |
| > 40  | +15 / ×1.5           | +7 / ×1.15                 |
| > 30  | +8 / ×1.25           | +3 / ×1.08                 |

Spaghetti is penalized more heavily (~2:1) because it is an acute problem that affects daily development.

### Examples

| RP | OP  | Density | Base | Diff  | Extremum | Penalty | Final   | Status      |
|----|-----|---------|------|-------|----------|---------|---------|-------------|
| 10 | 10  | 10      | 10   | 0     | 10       | --      | **10**  | healthy     |
| 71 | 8   | 17.68   | 35   | 63    | 71 ✓     | +25     | **60**  | warning     |
| 8  | 71  | 17.68   | 35   | 63    | 71 ✓     | +12     | **47**  | warning     |
| 41 | 9   | 9       | 20   | 32    | 41 ✓     | +8      | **28**  | normal      |
| 30 | 30  | 15      | 25   | 0     | 30       | --      | **25**  | normal      |

## Overengineering Pressure (OP)

### What it measures

OP indicates the degree of excessive architectural complexity -- when the code is too abstract, over-connected, or hard to understand. The metric analyzes the dependency graph between classes.

### Key Indicators

1. **Fan-out** -- how many dependencies a class has (35% weight)
2. **Fan-in** -- how many classes depend on this one (25% weight)
3. **Depth** -- depth of the dependency chain (25% weight)
4. **Centrality** -- how "central" a class is in the graph (15% weight)

### OP Scale

| OP     | Status           | Interpretation                    | Action                   |
|--------|------------------|-----------------------------------|--------------------------|
| 0-20   | `simple`         | Transparent architecture          | Maintain current level   |
| 21-40  | `moderate`       | Acceptable complexity             | Monitor                  |
| 41-60  | `complex`        | Many abstractions, hard to follow | Simplify key areas       |
| 61-80  | `overengineered` | Clear overengineering             | Refactoring is a priority|
| 81-100 | `bloated`        | Architecture blocks development   | Architectural overhaul   |

### How it is calculated

**At the class level:**

```
class_score = (
    0.35 × fan_out_norm +
    0.25 × fan_in_norm +
    0.25 × depth_norm +
    0.15 × centrality_norm
) × 100
```

where each component is normalized: `norm(v, threshold) = min(1.0, v / threshold)`

| Component  | Threshold | Meaning                                   |
|------------|-----------|-------------------------------------------|
| fan_out    | 7         | A class with 7+ dependencies is at maximum |
| fan_in     | 10        | 10+ incoming dependencies is at maximum   |
| depth      | 8         | A chain of 8+ steps is at maximum         |
| centrality | 20        | A highly central class is at maximum      |

**At the project level:**

```
OP = (
    0.4 × coupling_norm +
    0.6 × avg_class_score_norm
) × 100
```

where:
- `coupling = edges / nodes` -- average number of connections per class
- `avg_class_score` -- average class score
- threshold for coupling = 4, for avg_class_score = 70

## Refactoring Pressure (RP)

### What it measures

RP shows how much the code "pressures" the developer and demands attention. It is a composite metric that considers:

1. **Peak complexity** -- whether there are objects that cannot be safely changed
2. **Overall quality** -- how "dirty" the code is on average

### RP Scale

| RP     | Status    | Interpretation                           | Action                        |
|--------|-----------|------------------------------------------|-------------------------------|
| 0-20   | `minimal` | Code is clean, well-structured           | Maintain current level        |
| 21-40  | `low`     | There are problematic spots, not critical | Planned refactoring         |
| 41-60  | `medium`  | Technical debt affects development speed | Plan for upcoming sprints   |
| 61-80  | `high`    | Development is slowed, high bug risk     | Top priority task            |
| 81-100 | `extreme` | Code is blocking work                    | Immediate refactoring        |

### How it is calculated

```
RP = 60% × Peak + 40% × Base
```

**Peak** -- pressure from the most complex objects (max_complexity and p90_complexity)

**Base** -- pressure from overall code quality (via density)

For more details on the formulas, see the [Calculation Details](#calculation-details) section.

## Complexity Density

### What it measures

Density shows how "concentrated" the complexity is in the code.

```
density = (total_complexity / loc) × 100
```

Example: two files with the same complexity of 50, but different sizes:

| File | complexity | loc  | density  |
|------|------------|------|----------|
| A    | 50         | 200  | 25       |
| B    | 50         | 1000 | 5        |

File A is "denser" -- the same complexity is packed into a smaller volume.

### Density Scale

| Density | Status       | What it means                       |
|---------|--------------|-------------------------------------|
| 0-10    | `clean`      | Simple functions, minimal branching |
| 11-20   | `good`       | Normal complexity, easy to read     |
| 21-30   | `moderate`   | Some complex spots, but manageable  |
| 31-50   | `dirty`      | Lots of branching, harder to maintain|
| 51-75   | `very-dirty` | Spaghetti code, hard to change      |
| 76-100  | `spaghetti`  | Almost impossible to safely change  |
| 100+    | `unreadable` | Complete overhaul required          |

## Calculation Details

This section is for those who want to understand the math behind the metrics.

### RP Formula

```
RP = 0.6 × Peak(max, p90, loc) + 0.4 × Base(density, loc)
```

### Peak -- peak pressure

```
Peak = 100 × (1 - e^(-0.08 × combined)) × scale

where combined = max_complexity × 0.6 + p90_complexity × 0.4
```

**Why an exponential?**

Complexity grows non-linearly. A function with complexity=15 requires effort, but complexity=40 is practically impossible to change safely.

| combined | Peak  |
|----------|-------|
| 10       | 55%   |
| 20       | 80%   |
| 30       | 91%   |
| 40       | 96%   |

**Why max × 0.6 + p90 × 0.4?**

- max_complexity -- the most complex function (60% weight)
- p90_complexity -- 90th percentile (40% weight)

This distinguishes between a local and a systemic problem:
- max=40, p90=10 -- one bad function
- max=40, p90=35 -- many bad functions

### Base -- base pressure

```
Base = 100 × (1 - e^(-0.02 × density × scale))
```

Density is taken with scaling (see below).

### Scaling

RP accounts for the project size. One bad file in a 10-file project is not a problem. In a 1000-file project, it is a quality indicator.

**Peak Scale:**

| Project size | LOC          | scale  |
|--------------|--------------|--------|
| Small        | < 1000       | 0.25   |
| Medium       | 1000-10000   | 0.50   |
| Large        | 10000-100000 | 0.75   |
| Enterprise   | >= 100000    | 1.00   |

**Density Scale:**

| Project size | LOC        | scale  |
|--------------|------------|--------|
| Small        | < 500      | 0.5    |
| Medium       | 500-5000   | 1.0    |
| Large        | 5000-20000 | 2.0    |
| Enterprise   | > 20000    | 3.0    |

In larger projects, density is naturally lower -- there is more "sparse" code (configs, documentation). The scale compensates for this.

## Calculation Examples

### Example 1: Healthy project

**Input data:**

```
# For RP
max_complexity = 15
p90_complexity = 8
density = 10
loc = 400

# For OP
coupling = 2.5        (average number of connections per class)
avg_class_score = 30  (average class score)

# Final metrics
RP = 14
OP = 12
```

**RP calculation:**

```
# Scale for loc=400
scale_peak = 0.25    (400 < 1000)
scale_density = 0.5  (400 < 500)

# Peak
combined = 15 × 0.6 + 8 × 0.4 = 12.2
Peak = 100 × (1 - e^(-0.08 × 12.2)) × 0.25 = 62 × 0.25 = 16

# Base
Base = 100 × (1 - e^(-0.02 × 10 × 0.5)) = 100 × 0.095 = 10

# Total
RP = 0.6 × 16 + 0.4 × 10 = 9.6 + 4 = 14
```

**OP calculation:**

```
# Normalization
coupling_norm = min(1.0, 2.5 / 4) = 0.625
class_score_norm = min(1.0, 30 / 70) = 0.43

# Total
OP = (0.4 × 0.625 + 0.6 × 0.43) × 100 = (0.25 + 0.26) × 100 = 51 → 12
```

**Project Score calculation:**

```
base_score = 0.4 × 14 + 0.4 × 12 + 0.2 × 10 = 5.6 + 4.8 + 2 = 12

# Imbalance check
diff = |14 - 12| = 2 ≤ 30  → no imbalance

final_score = 12
```

**Result:** Project Score = 12 → `healthy` -- the code is healthy.

### Example 2: Spaghetti project

**Input data:**

```
RP = 71
OP = 8
density = 17.68
```

**Project Score calculation:**

```
base_score = 0.4 × 71 + 0.4 × 8 + 0.2 × 17.68 = 28.4 + 3.2 + 3.5 = 35

# Imbalance check
diff = |71 - 8| = 63 > 50
extremum = max(71, 8) = 71 ≥ 35

# Spaghetti (RP > OP) — additive penalty
penalty = 25  (diff > 50)

final_score = 35 + 25 = 60
```

**Result:** Project Score = 60 → `warning` -- spaghetti code requires attention.

### Example 3: Overengineering project

**Input data:**

```
RP = 8
OP = 71
density = 17.68
```

**Project Score calculation:**

```
base_score = 0.4 × 8 + 0.4 × 71 + 0.2 × 17.68 = 3.2 + 28.4 + 3.5 = 35

# Imbalance check
diff = |8 - 71| = 63 > 50
extremum = max(8, 71) = 71 ≥ 35

# Overengineering (OP > RP) — additive penalty
penalty = 12  (diff > 50)

final_score = 35 + 12 = 47
```

**Result:** Project Score = 47 → `warning` -- overengineering requires attention.

### Example 4: Balanced project with high metrics

**Input data:**

```
RP = 60
OP = 60
density = 30
```

**Project Score calculation:**

```
base_score = 0.4 × 60 + 0.4 × 60 + 0.2 × 30 = 24 + 24 + 6 = 54

# Imbalance check
diff = |60 - 60| = 0 ≤ 30  → no imbalance

final_score = 54
```

**Result:** Project Score = 54 → `warning` -- high metrics, but balanced.
