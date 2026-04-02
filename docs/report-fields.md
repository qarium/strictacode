# strictacode Report Fields

This document describes all fields output in the strictacode report for each level of the code hierarchy.

## Report Levels

```
Project
├── Package[]
│   └── Module[]
│       ├── Class[]
│       │   └── Method[]
│       └── Function[]
```

---

## Project

The root level of the report. Describes the entire project as a whole.

### General Fields

| Field       | Type      | Description                                                                        |
|-------------|-----------|------------------------------------------------------------------------------------|
| `lang`      | `string`  | Project programming language. Possible values: `python`, `golang`, `javascript`, `kotlin` |
| `loc`       | `int`     | Total lines of code in the project (excluding comments and blank lines)            |
| `packages`  | `int`     | Number of packages in the project                                                  |
| `modules`   | `int`     | Number of modules (files) in the project                                           |
| `classes`   | `int`     | Number of classes in the project                                                   |
| `methods`   | `int`     | Number of methods in the project                                                   |
| `functions` | `int`     | Number of top-level functions in the project                                       |

### status

The project's health status. The structure is described in the [Status](#status) section.

### overengineering_pressure

Metric for excessive architectural complexity.

| Field           | Type    | Description                                  |
|-----------------|---------|----------------------------------------------|
| `score`         | `int`   | Overengineering Pressure value (0-100)       |
| `stat(modules)` | `Stat`  | Per-module statistics (see [Stat](#stat))    |

**Score scale:**

| Score  | Status           | Interpretation                       |
|--------|------------------|--------------------------------------|
| 0-20   | `simple`         | Simple architecture                  |
| 21-40  | `moderate`       | Moderate complexity                  |
| 41-60  | `complex`        | Many abstractions                    |
| 61-80  | `overengineered` | Clear overengineering                |
| 81-100 | `bloated`        | Architecture is blocking development |

### refactoring_pressure

Metric for refactoring pressure.

| Field           | Type    | Description                                  |
|-----------------|---------|----------------------------------------------|
| `score`         | `int`   | Refactoring Pressure value (0-100)           |
| `stat(modules)` | `Stat`  | Per-module statistics (see [Stat](#stat))    |

**Score scale:**

| Score  | Status    | Interpretation                        |
|--------|-----------|----------------------------------------|
| 0-20   | `minimal` | Code is clean                          |
| 21-40  | `low`     | There are some problematic areas       |
| 41-60  | `medium`  | Technical debt affects velocity       |
| 61-80  | `high`    | Development is slowed down            |
| 81-100 | `extreme` | Code is blocking work                 |

### complexity

Code complexity metric.

| Field           | Type     | Description                                  |
|-----------------|----------|----------------------------------------------|
| `score`         | `int`    | Total cyclomatic complexity                  |
| `density`       | `float`  | Complexity density: `(score / loc) * 100`    |
| `stat(modules)` | `Stat`   | Per-module statistics (see [Stat](#stat))    |

**Density scale:**

| Density | Status       | Interpretation        |
|---------|--------------|-----------------------|
| 0-10    | `clean`      | Simple code           |
| 11-20   | `good`       | Normal complexity     |
| 21-30   | `moderate`   | Some complex areas    |
| 31-50   | `dirty`      | Many branches         |
| 51-75   | `very-dirty` | Spaghetti code        |
| 76-100  | `spaghetti`  | Hard to change        |
| 100+    | `unreadable` | Needs a rewrite       |

---

## Package

A package is a logical grouping of modules (a directory).

| Field                      | Type      | Description                                                                      |
|----------------------------|-----------|----------------------------------------------------------------------------------|
| `name`                     | `string`  | Package name (directory name)                                                    |
| `dir`                      | `string`  | Path to the package directory                                                    |
| `loc`                      | `int`     | Number of lines of code in the package                                           |
| `modules`                  | `int`     | Number of modules in the package                                                 |
| `status`                   | `Status`  | Health status (see [Status](#status))                                            |
| `overengineering_pressure` | `Metric`  | Same structure as [Project.overengineering_pressure](#overengineering_pressure)  |
| `refactoring_pressure`     | `Metric`  | Same structure as [Project.refactoring_pressure](#refactoring_pressure)          |
| `complexity`               | `Metric`  | Same structure as [Project.complexity](#complexity)                              |

---

## Module

A module is a single source code file.

| Field                      | Type      | Description                                                                      |
|----------------------------|-----------|----------------------------------------------------------------------------------|
| `name`                     | `string`  | Module name (file name)                                                          |
| `file`                     | `string`  | Path to the file                                                                 |
| `loc`                      | `int`     | Number of lines of code in the module                                            |
| `classes`                  | `int`     | Number of classes in the module                                                  |
| `functions`                | `int`     | Number of top-level functions in the module                                      |
| `status`                   | `Status`  | Health status (see [Status](#status))                                            |
| `overengineering_pressure` | `Metric`  | Same structure as [Project.overengineering_pressure](#overengineering_pressure), but `stat` is per-class |
| `refactoring_pressure`     | `Metric`  | Only the `score` field (no statistics)                                           |
| `complexity`               | `Metric`  | Same structure as [Project.complexity](#complexity), but `stat` is per-class and per-function |

---

## Class

A class in object-oriented code.

| Field                      | Type      | Description                                                                      |
|----------------------------|-----------|----------------------------------------------------------------------------------|
| `name`                     | `string`  | Class name                                                                       |
| `file`                     | `string`  | Path to the file containing the class                                            |
| `loc`                      | `int`     | Number of lines of code in the class                                             |
| `methods`                  | `int`     | Number of methods in the class                                                   |
| `status`                   | `Status`  | Health status (see [Status](#status))                                            |
| `overengineering_pressure` | `Metric`  | Only the `score` field. Based on fan-out, fan-in, depth, and centrality in the dependency graph |
| `complexity`               | `Metric`  | Same structure as [Project.complexity](#complexity), but `stat` is per-method    |

---

## Method

A class method.

| Field         | Type      | Description                                          |
|---------------|-----------|------------------------------------------------------|
| `name`        | `string`  | Method name                                           |
| `file`        | `string`  | Path to the file containing the method               |
| `class`       | `string`  | Name of the class the method belongs to              |
| `loc`         | `int`     | Number of lines of code in the method                |
| `closures`    | `int`     | Number of nested functions (closures) in the method  |
| `status`      | `Status`  | Health status (see [Status](#status))                |
| `complexity`  | `Metric`  | See the [complexity (Method/Function)](#complexity-methodfunction) structure below |

---

## Function

A top-level function (not a class method).

| Field        | Type      | Description                                    |
|--------------|-----------|------------------------------------------------|
| `name`       | `string`  | Function name                                  |
| `file`       | `string`  | Path to the file containing the function       |
| `loc`        | `int`     | Number of lines of code in the function        |
| `closures`   | `int`     | Number of nested functions in the function body|
| `status`     | `Status`  | Health status (see [Status](#status))          |
| `complexity` | `Metric`  | See the structure below                        |

### complexity (Method/Function)

Complexity structure for methods and functions.

| Field             | Type     | Description                                   |
|-------------------|----------|-----------------------------------------------|
| `score`           | `int`    | Cyclomatic complexity                         |
| `total`           | `int`    | Total complexity including closures            |
| `density`         | `float`  | Complexity density: `(score / loc) * 100`     |
| `stat(closures)`  | `Stat`   | Per-closure statistics (see [Stat](#stat))    |

---

## Common Structures

### Stat

Statistics over child elements. Used at all report levels.

| Field | Type   | Description                    |
|-------|--------|--------------------------------|
| `avg` | `int`  | Average value                  |
| `min` | `int`  | Minimum value                  |
| `max` | `int`  | Maximum value                  |
| `p50` | `int`  | Median (50th percentile)       |
| `p90` | `int`  | 90th percentile                |

**Example:**
```
stat(modules):
  + avg: 8
  + min: 1
  + max: 24
  + p50: 6
  + p90: 16
```

### Status

Health status structure. The same at all levels.

| Field         | Type        | Description                                     |
|---------------|-------------|-------------------------------------------------|
| `name`        | `string`    | Status name                                     |
| `score`       | `int`       | Numeric value (0-100)                           |
| `reasons`     | `string[]`  | Reasons for the current status (optional)       |
| `suggestions` | `string[]`  | Improvement recommendations (optional)          |

**status.name scale:**

| Score  | Status      | Interpretation         |
|--------|-------------|------------------------|
| 0-20   | `healthy`   | Code is healthy        |
| 21-40  | `normal`    | Normal state           |
| 41-60  | `warning`   | There are problems     |
| 61-80  | `critical`  | Critical state         |
| 81-100 | `emergency` | Emergency situation    |

### Metric

Common metric structure (overengineering_pressure, refactoring_pressure, complexity).

| Field     | Type     | Description                                       |
|-----------|----------|---------------------------------------------------|
| `score`   | `int`    | Metric value (0-100)                              |
| `density` | `float`  | Density (only for complexity)                     |
| `stat`    | `Stat`   | Per-child-element statistics (optional)           |

---

## Report Formats

### Text (default)

```bash
strictacode analyze ./src
strictacode analyze ./src --short
strictacode analyze ./src --details
```

- `--short` -- Project level only
- default -- Project + Packages + Modules
- `--details` -- includes Class, Method, Function levels

### JSON

```bash
strictacode analyze ./src --format json
```

Returns a structure with fields matching those described above.

---

## Compare Report Fields

The `compare` command produces a diff report containing the directional difference between two analysis results (current − baseline). Positive values mean the current result is higher. Use `--details` to include the full metrics for both baseline and current.

### Diff Structure

| Field                       | Type   | Description                              |
|-----------------------------|--------|------------------------------------------|
| `diff.score`                | int    | Directional difference in project score (current − baseline)     |
| `diff.complexity_density`   | float  | Directional difference in complexity density (current − baseline) |
| `diff.refactoring_pressure` | int    | Directional difference in refactoring pressure (current − baseline) |
| `diff.overengineering_pressure` | int | Directional difference in overengineering pressure (current − baseline) |

### Details Structure (with `--details`)

When `--details` is specified, the report includes the full metrics for both results:

| Field                       | Type   | Description                                |
|-----------------------------|--------|--------------------------------------------|
| `<name>.score`              | int    | Project score from the result              |
| `<name>.complexity_density` | float  | Complexity density from the result         |
| `<name>.refactoring_pressure` | int  | Refactoring pressure from the result       |
| `<name>.overengineering_pressure` | int | Overengineering pressure from the result  |

where `<name>` is `baseline` for the first result and `current` for the second.

### JSON Example

```bash
strictacode compare baseline.json current.json --format json --details --output diff.json
```

```json
{
  "diff": {
    "score": 7,
    "complexity_density": 1.7,
    "refactoring_pressure": 7,
    "overengineering_pressure": 2
  },
  "baseline": {
    "score": 35,
    "complexity_density": 12.4,
    "refactoring_pressure": 55,
    "overengineering_pressure": 20
  },
  "current": {
    "score": 42,
    "complexity_density": 14.1,
    "refactoring_pressure": 62,
    "overengineering_pressure": 22
  }
}
```

### Text Example

```bash
strictacode compare baseline.json current.json --details
```

```
Diff:
  * score: 7
  * complexity_density: 1.7
  * refactoring_pressure: 7
  * overengineering_pressure: 2

---

Baseline:
  * score: 35
  * complexity_density: 12.4
  * refactoring_pressure: 55
  * overengineering_pressure: 20

---

Current:
  * score: 42
  * complexity_density: 14.1
  * refactoring_pressure: 62
  * overengineering_pressure: 22
```

---

## Report Example

```
Project:
  * lang: python
  * loc: 3235
  * packages: 6
  * modules: 20
  * classes: 34
  * methods: 153
  * functions: 36
  * status:
    - name: healthy
    - score: 18
  * overengineering_pressure:
    - score: 8
    - stat(modules):
      + avg: 3
      + min: 0
      + max: 9
      + p50: 2
      + p90: 8
  * refactoring_pressure:
    - score: 34
    - stat(modules):
      + avg: 8
      + min: 1
      + max: 24
      + p50: 6
      + p90: 16
  * complexity:
    - score: 242
    - density: 7.48
    - stat(modules):
      + avg: 12
      + min: 2
      + max: 52
      + p50: 6
      + p90: 26

---

Packages:
  * strictacode:
    - dir: strictacode
    - loc: 1429
    - modules: 7
    - status:
      + name: healthy
      + score: 19
    - overengineering_pressure:
      + score: 9
      + stat(modules):
        - avg: 1
        - min: 0
        - max: 5
        - p50: 0
        - p90: 4
    - refactoring_pressure:
      + score: 34
      + stat(modules):
        - avg: 8
        - min: 3
        - max: 24
        - p50: 6
        + p90: 15
    - complexity:
      + score: 104
      + density: 7.28
      + stat(modules):
        - avg: 15
        - min: 2
        - max: 52
        + p50: 7
        + p90: 32

---

Modules:
  * utils.py:
    - file: strictacode/utils.py
    - loc: 112
    - classes: 0
    - functions: 7
    - status:
      + name: healthy
      + score: 19
    - overengineering_pressure:
      + score: 0
      + stat(classes):
        - avg: 0
        - min: 0
        - max: 0
        + p50: 0
        + p90: 0
    - refactoring_pressure:
      + score: 24
    - complexity:
      + score: 52
      + density: 46.43
      + stat(classes+functions):
        - avg: 7
        - min: 4
        - max: 14
        + p50: 8
        + p90: 11

---

Classes:
  * Metric:
    - file: strictacode/calc/score.py
    - loc: 16
    - methods: 2
    - status:
      + name: normal
      + score: 21
    - overengineering_pressure:
      + score: 0
    - complexity:
      + score: 6
      + density: 37.5
      + stat(methods):
        - avg: 5
        - min: 5
        - max: 5
        + p50: 5
        + p90: 5

---

Methods:
  * number_of_edges:
    - file: strictacode/graph.py
    - class: DiGraph
    - loc: 2
    - closures: 0
    - status:
      + name: warning
      + score: 60
    - complexity:
      + score: 2
      + total: 2
      + density: 100.0
      + stat(closures):
        - avg: 0
        - min: 0
        + max: 0
        + p50: 0
        + p90: 0

---

Functions:
  * lines_of_code:
    - file: strictacode/utils.py
    - loc: 35
    - closures: 1
    - status:
      + name: normal
      + score: 29
    - complexity:
      + score: 14
      + total: 17
      + density: 40.0
      + stat(closures):
        - avg: 3
        - min: 3
        + max: 3
        + p50: 3
        + p90: 3
```