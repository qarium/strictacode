# Usage Examples

This documentation contains real-world strictacode usage scenarios with step-by-step workflows.

## Team Processes

### CI/CD Gates

**Context:** Code quality degradation needs to be blocked in the pipeline. A pull request with bad code should not land in main.

**Approach 1: Absolute thresholds**

Block PRs that push the codebase above a quality limit:

```bash
strictacode analyze . --threshold "score=60,rp=70,op=50,density=30"
```

Exits with code 1 if any metric exceeds the threshold. Add this as a CI step after tests — no scripts needed.

**Approach 2: Relative thresholds (delta against baseline)**

Track quality degradation over time by comparing against a saved baseline using the `compare` command:

```bash
strictacode analyze . --format json --output current.json
strictacode compare baseline.json current.json --threshold "score=10,rp=5,op=5,density=5"
```

**Workflow:**
1. Establish a baseline: run the analysis on the current main and save `baseline.json` in the repository
2. Add a CI step after tests that:
   - Runs `strictacode analyze . --format json --output current.json`
   - Runs `strictacode compare baseline.json current.json --threshold score=10,rp=5`
3. The PR is blocked if the diff exceeds the threshold (exit code 1)
4. After merging into main — update `baseline.json`

The `compare` command calculates the absolute difference between two results for all four metrics (Score, Complexity Density, Refactoring Pressure, Overengineering Pressure) and checks each against the threshold.

---

### Sprint Retrospective

**Context:** The team is running a retro. Code quality is being discussed. Opinions diverge: "the code is fine" vs. "everything is falling apart." Objective data is needed.

**Command:**
```bash
# Before the sprint
strictacode analyze . --format json > sprint-start.json

# After the sprint
strictacode analyze . --format json > sprint-end.json
```

**Result:** Two snapshots of the codebase state.

**Workflow:**
1. Run the analysis at the start of the sprint and save the baseline
2. During the sprint — do not touch the metrics, just work
3. At the end of the sprint — run the analysis again
4. Compare metrics:
   - RP increased → technical debt accumulated, the next sprint needs time allocated for cleanup
   - OP increased → abstractions were added; verify whether they are needed or premature
   - Density increased → code is getting "dirtier," stricter code reviews are needed
5. Discuss at the retro:
   - Which modules deteriorated and why?
   - Is this normal growth or a problem?
   - What should be done in the next sprint?
6. Save sprint-end.json as the baseline for the next sprint

## Getting to Know a Project

### Onboarding a New Developer

**Context:** A new developer joins the project. The first task is to figure out where the complex code is and where it is safe to work. Without strictacode, this takes weeks of reading code and accidental discoveries.

**Command:**
```bash
strictacode analyze . --details
```

**Result:** Metrics by modules/packages — where RP is high (messy code), where OP is high (complex dependencies), and where density is off the charts.

**Workflow:**
1. Run the analysis with `--details`
2. Find modules with `status: healthy` — these are the best places to start working
3. Look at modules with `RP > 60` — these are the hardest to change
4. Examine `density` — high density means "spaghetti in a single file"
5. Build a mental map: "green zones" vs. "red zones"

---

### Evaluating a Legacy Project

**Context:** A tech lead steps into a legacy project. The goal is to quickly understand the state of the codebase and answer the question: "where do I start?"

**Command:**
```bash
strictacode analyze . --short
```

**Result:** Project Score, RP, OP, density — an overall picture of health.

**Workflow:**
1. Run a short analysis to get the Project Score
2. Interpret the score using the scale (healthy/normal/warning/critical/emergency)
3. Compare RP and OP:
   - RP >> OP → spaghetti code, clean up the functions
   - OP >> RP → overengineering, simplify the architecture
   - Both high → crisis, isolate and rewrite
4. Prepare a report for stakeholders with concrete metrics

## Day-to-Day Development

### Planning Unit Tests

**Context:** A developer is deciding which functions to cover with unit tests first. Time is limited — the goal is to maximize impact.

**Command:**
```bash
strictacode analyze . --details
```

**Result:** Breakdown by modules/classes/functions with complexity metrics.

**Workflow:**
1. Run the analysis with `--details`
2. Sort functions by `complexity` — functions with complexity > 15 are harder to test and break more often
3. Look at `density` in the module — high density means tangled code, tests will be difficult
4. Prioritization: start with high-complexity functions in modules with low OP (fewer mocks needed)
5. Defer functions in modules with high OP — those need integration tests

---

### Planning Integration Tests for Services

**Context:** QA is planning testing for a microservice architecture. The goal is to understand which services carry higher risk when changed and which carry less.

**Command:**
```bash
# For each service
strictacode analyze ./service-a --short
strictacode analyze ./service-b --short
strictacode analyze ./service-c --short
```

**Result:** Project Score, RP, OP, density for each service.

**Workflow:**
1. Run the analysis for each service separately
2. Compare metrics across services:
   - High RP — service with "messy" code, changes are risky
   - High OP — complex architecture, higher chance of breaking integrations
   - High density — a lot of logic in one place, harder to cover with tests
3. Testing priority:
   - `status: critical/emergency` — maximum attention, regression tests are mandatory
   - `status: warning` — standard coverage + integration smoke tests
   - `status: healthy/normal` — minimal set of smoke tests
4. Allocate a time buffer for bugs in services with high RP

---

### Prioritizing API Endpoints for Testing

**Context:** A service has many API endpoints, and testing all of them is impossible. The goal is to figure out which endpoints to cover with tests first.

**Command:**
```bash
strictacode analyze . --details
```

**Result:** Breakdown by packages/modules with metrics.

**Workflow:**
1. Run the analysis with `--details`
2. Find packages with `status: warning` and above — these are problem areas
3. Map packages to API endpoints:
   - Which package handles which endpoint
   - Which endpoints depend on modules with high RP
4. Endpoint testing priority:
   - Endpoints backed by packages with `status: critical` — test first, maximum coverage
   - Endpoints backed by packages with `status: warning` — standard coverage
   - Endpoints backed by packages with `status: healthy` — minimal smoke tests
5. Endpoints that touch multiple problem modules — candidates for end-to-end tests

## Decision Making

### Choosing Whether to Rewrite or Refactor a Package/Service

**Context:** An entire package or service is problematic. A decision needs to be made at the architectural unit level.

**Command:**
```bash
strictacode analyze .
```

**Result:** Project metrics broken down by packages/modules.

**Workflow:**
1. Run the analysis of the entire project
2. Find the relevant package/service in the results
3. Assess the overall state using its Project Score:
   - Score < 40 — can be refactored incrementally
   - Score 40-60 — serious issues, a plan is needed
   - Score > 60 — critical state
4. Look at the distribution of problems within:
   - Problems in 1-2 submodules → isolate and refactor/rewrite only those
   - Problems evenly distributed → systemic architectural issue
5. Evaluate coupling (OP): high OP means the module is heavily tied to others. Rewriting will break integrations.
6. Decision:
   - Local problems → targeted refactoring/rewriting
   - Systemic problems + low OP → candidate for rewriting
   - Systemic problems + high OP → gradual refactoring while preserving interfaces

---

### Justifying Refactoring to Management

**Context:** Time needs to be allocated for refactoring within a sprint. Management wants to know: "why?" and "how much?" A subjective "the code is bad" does not work.

**Command:**
```bash
strictacode analyze . --short
strictacode analyze . --format json > quality-baseline.json
```

**Result:** Metrics in a human-readable format + JSON for tracking progress.

**Workflow:**
1. Run the analysis and save the baseline
2. Frame the problem using metrics:
   - "RP = 72 — this means every code change carries a high risk of bugs"
   - "Density = 58 — the code is spaghetti-like, task completion time doubles"
3. Show the trend: run the analysis on code from 3 months ago (via git checkout), compare the results
4. Translate into business language:
   - High RP → slower feature delivery, more bugs in production
   - High OP → harder to onboard new developers, longer code reviews
5. Propose a plan: "We will reduce RP from 72 to 40 in 2 sprints, which will speed up development by X%"
6. After refactoring: run the analysis again and show the improvement

## AI-Assisted Development

### Analyzing Code Quality with an AI Agent

**Context:** A developer wants an objective code quality assessment with concrete improvement suggestions. Instead of reading metrics manually and figuring out what to do, the AI agent does the interpretation and produces a prioritized plan.

**Setup:**

Install strictacode as a skill for the AI agent:

```bash
# Claude Code
strictacode install agent-skill --agent claude

# Cursor
strictacode install agent-skill --agent cursor

# OpenAI Codex
strictacode install agent-skill --agent codex
```

Supported agents: `claude`, `cursor`, `codex`, `gemini`, `antigravity`.

**Usage:**

```text
Проанализируй качество кода с strictacode
```

The agent automatically runs the analysis, interprets all metrics, identifies hotspots by reading the actual source code, and produces a prioritized improvement plan with concrete actions, file locations, and expected effects.

**Workflow:**
1. Install the skill once: `strictacode install agent-skill --agent <agent>`
2. Open the AI agent in the project directory
3. Send the prompt
4. The agent runs `strictacode analyze . --details --format json`
5. Review the output: project summary, metric breakdown, red flags, pain points, improvement plan (P0/P1/P2)
6. Use the plan to guide refactoring work

**Result:** A structured analysis with:
- Project type diagnosis (Healthy / Spaghetti / Overengineering / Crisis)
- Top problematic functions and classes with line numbers
- Concrete refactoring steps ordered by priority
- Expected metric improvements

For details on what the agent analyzes and how it interprets each metric, see [CLI Reference — agent-skill](cli-reference.md#strictacode-install-agent-skill).

## Dashboard Integration

### Tracking Code Quality Over Time

**Context:** The team wants to track code quality metrics on a dashboard (Grafana, Metabase, custom frontend). The workflow: strictacode generates a JSON report, CI sends it to an API, the dashboard visualizes trends.

**Configuration:**

Create `.strictacode.yml` in the project root to control the volume of data sent to the dashboard:

```yaml
reporter:
  top:
    packages: 10
    modules: 20
    classes: 30
    methods: 50
    functions: 50
```

Adjust the `top` values based on project size. Larger values produce more data — useful for dashboards but heavier on the API.

**Generating the report:**

Use `--details` to include analytics for functions, methods, and classes, and `--format json` for structured output:

```bash
strictacode analyze . --details --format json --output report.json
```

**Sending to an API:**

```bash
curl -X POST https://your-dashboard-api.example.com/api/metrics \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $DASHBOARD_TOKEN" \
  --data @report.json
```

The server receives the full JSON report and can store metrics per project, branch, and timestamp.

**CI integration (GitHub Actions):**

```yaml
name: Code Quality Dashboard

on:
  push:
    branches: [main]

jobs:
  metrics:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install strictacode
        run: pip install strictacode

      - name: Analyze
        run: strictacode analyze . --details --format json --output report.json

      - name: Send to dashboard
        env:
          DASHBOARD_TOKEN: ${{ secrets.DASHBOARD_TOKEN }}
        run: |
          curl -X POST https://your-dashboard-api.example.com/api/metrics \
            -H "Content-Type: application/json" \
            -H "Authorization: Bearer $DASHBOARD_TOKEN" \
            --data @report.json
```

**Key JSON fields for dashboard:**

| Field                                            | Description                          |
|--------------------------------------------------|--------------------------------------|
| `project.status.score`                           | Overall project health (0-100)       |
| `project.refactoring_pressure.score`             | Refactoring pressure (0-100)         |
| `project.overengineering_pressure.score`         | Overengineering pressure (0-100)     |
| `project.complexity.density`                     | Complexity density                   |
| `project.loc`                                    | Lines of code                        |
| `project.packages`                               | Number of packages                   |
| `project.modules`                                | Number of modules                    |
| `packages[].name`                                | Package name                         |
| `packages[].status.score`                        | Package health (0-100)               |
| `packages[].refactoring_pressure.score`          | Package RP                           |
| `packages[].complexity.density`                  | Package complexity density           |

For the full JSON structure, see [Report Fields](report-fields.md).

**Workflow:**
1. Create `.strictacode.yml` with desired `reporter.top` values
2. Set up an API endpoint that accepts the JSON report
3. Add the CI workflow (or run manually during development)
4. Build dashboard visualizations using the stored metrics:
   - Project Score trend over time
   - RP and OP per branch
   - Complexity density by package
   - Comparison across projects/services
