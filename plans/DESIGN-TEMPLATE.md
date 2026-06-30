# Design: {{PROJECT_NAME}}

## Architecture

This experiment uses the standard agent experiment loop:

```
ExperimentApp → AgentExperiment → AgentInvoker → CascadedJury → ResultStore
                       │                                            ↓
                       │ (per item, on by default)        ComparisonEngine
                       ▼                                            ↓
              canonical agent-journal                     GrowthStoryReporter
              events.jsonl + analysis.jsonl
                       │
                       ▼
              agent_control_theory.load_journal → Markov / cost-weighted V(EXPLORE)
```

`AgentExperiment` owns the run-journal lifecycle: for every item it opens a journal Run on
`JsonFileStorage` (rooted under `outputDir`), records each `PhaseCapture`, and writes the immutable
events plus derived per-tool `StepCostEvent`s. The **AgentInvoker writes no journal code** — it just
returns `PhaseCapture`s. The result store remains the experiment summary; the **journal is the trace
source of truth** the analysis layer consumes.

## Domain Agent

**AgentInvoker implementation:** `{{Domain}}AgentInvoker`

_Describe what the agent does, how it interacts with the workspace, and what
domain-specific setup/teardown is needed._

**Invocation pattern:**
- Single-phase: `TemplateAgentInvoker` → `AgentClient.goal(prompt).run()`
- Two-phase: `TwoPhaseTemplateAgentInvoker` → `ClaudeSyncClient` explore + act sessions

## Judge Tiers

| Tier | Policy | Judge | Type | What it checks |
|------|--------|-------|------|---------------|
| 0 | REJECT_ON_ANY_FAIL | BuildSuccessJudge | Deterministic | Build compiles and tests pass |
| 1 | REJECT_ON_ANY_FAIL | _PreservationJudge_ | Deterministic | No regressions from baseline |
| 2 | REJECT_ON_ANY_FAIL | _{{Domain}}Judge_ | Custom | Domain-specific evaluation |
| 3 | FINAL_TIER | _QualityJudge_ | Agent-based | Practice adherence (optional) |

**Tier design principles:**
- Tier 0: Cheap, fast, deterministic gates — reject early
- Tier 1: Preservation checks — ensure no regressions
- Tier 2: Domain-specific measurement — the experiment's core metric
- Tier 3: Qualitative evaluation — expensive, run only on tier-2 survivors

## Variant Ablation

Variants are **empirically motivated** — each exists because the previous variant's analysis revealed a specific gap. The table below shows the starting plan; actual variants will evolve based on measurement.

| Variant | Prompt | Knowledge | Phase | Iteration Metadata |
|---------|--------|-----------|-------|--------------------|
| control | v0-naive | none | single | finding: null, hypothesis: "Establish baseline" |
| variant-a | v1-hardened | none | single | finding: _from control analysis_, hypothesis: _TBD_ |
| variant-b | v2-with-kb | targeted files | single | finding: _from variant-a analysis_, hypothesis: _TBD_ |

**Iteration metadata** links each variant to its motivating observation:

```yaml
iteration:
  finding: "v0 BUILD→FIX loop amplification 3.2"
  hypothesis: "Structured execution steps reduce fix loops"
```

Pre-planning more than 2–3 variants is fine for hypothesis-driven experiments, but fill in `finding` and `hypothesis` after each run, not before.

## Measurement Strategy

**Trace source of truth:** the canonical agent-journal (`events.jsonl` + `analysis.jsonl`), written
on-by-default per item. The analysis layer reads it via `agent_control_theory.load_journal(results/)`
— **not** a result-store ETL. Per-tool cost (`attributed_cost_usd`) is an **allocation, not a
measurement** (output-token-proportional; `attribution_method` is `OUTPUT_TOKEN_PROPORTIONAL` when
precise, `EVEN_SPLIT` for the coarse fallback) — report it as such and filter coarse runs from the
data alone.

**Loss dimensions to track:**

| Dimension | Signal | Tool |
|-----------|--------|------|
| _Outcome_ | _Pass rate, judge scores_ | _GrowthStoryReporter_ |
| _Behavioral_ | _Loop amplification_ | _make_markov_analysis.py (over the canonical journal)_ |
| _Knowledge_ | _Search state frequency_ | _Markov state distribution_ |
| _Cost_ | _Cost-weighted V(EXPLORE), per-tool $_ | _load_journal → cost_weighted_explore (allocation)_ |

**Regression criteria:** A change is a regression if any per-judge score decreases by more than _X_ across the dataset, even if the aggregate improves.

## Two-Phase Pattern

For variants using two-phase invocation (explore + act):

**Phase 1 — Explore:**
- Agent reads codebase and knowledge files
- Creates a plan document (e.g., `PLAN.md`)
- Does NOT modify any source code

**Phase 2 — Act:**
- Same session — agent has full context from Phase 1
- Executes the plan created in Phase 1
- Makes all code changes

**Benefits:** Forces structured knowledge consumption before action. Session
continuity means no context loss between planning and execution.

## Dataset

_Describe the benchmark dataset: what projects, how many items, what makes them
representative._

## Knowledge Strategy

```
knowledge/
├── index.md              ← Routing table (JIT navigation)
└── domain/               ← Domain-specific knowledge files
    ├── fundamentals.md   ← Core concepts
    ├── patterns.md       ← Best practices
    └── anti-patterns.md  ← What to avoid
```

**Knowledge injection strategies:**
- `knowledgeFiles: []` → no knowledge (control)
- `knowledgeFiles: [specific.md, ...]` → targeted injection (variant-b)
- `knowledgeFiles: [index.md]` → full tree copy with routing (variant-c, variant-d)
