# Getting Started

This guide walks you through running your first analysis and understanding the results.

## Step 1: Install

```bash
pip install strictacode
```

See [Installation](installation.md) for details.

## Step 2: Run Your First Analysis

Navigate to your project directory and run:

```bash
strictacode analyze . --short
```

You'll see output like this:

```
Project:
  * status:
    - name: warning
    - score: 58          ← Project health (0-100, lower is better)
  * refactoring_pressure:
    - score: 72          ← How much the code "pressures" the developer
  * overengineering_pressure:
    - score: 18          ← How over-engineered the architecture is
  * complexity:
    - density: 42.5      ← Concentration of complexity
```

## Step 3: Understand the Metrics

| Metric                   | What it Measures         | Good  | Bad   |
|--------------------------|--------------------------|-------|-------|
| **Project Score**        | Overall health           | 0-20  | 60+   |
| **Refactoring Pressure** | Pressure to refactor     | 0-40  | 60+   |
| **Overengineering Pressure** | Excessive complexity  | 0-40  | 60+   |
| **Complexity Density**   | Complexity concentration | < 20  | > 50  |

## Step 4: Diagnose Your Project

Compare **Refactoring Pressure (RP)** and **Overengineering Pressure (OP)**:

- **RP high, OP low** → Spaghetti code — clean up functions
- **OP high, RP low** → Overengineering — simplify architecture
- **Both high** → Crisis — isolate and rewrite
- **Both low** → Healthy — monitor

For a detailed diagnosis walkthrough, see [Interpretation](interpretation.md).

## Step 5: Drill Down

Use the `--details` flag to see which specific modules, classes, and functions are problematic:

```bash
strictacode analyze . --details
```

This adds class, method, and function-level breakdowns so you can pinpoint exactly where to focus.

## What's Next

- [CLI Reference](cli-reference.md) — all commands and flags
- [Interpretation](interpretation.md) — detailed diagnostic scenarios
- [Configuration](configuration.md) — customize analysis with config files
- [Examples](examples.md) — real-world usage scenarios
