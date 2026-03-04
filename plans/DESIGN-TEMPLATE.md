# Design: {{PROJECT_NAME}}

## Architecture

This experiment uses the standard agent experiment loop:

```
ExperimentApp → ExperimentRunner → AgentInvoker → CascadedJury → ResultStore
                                                                    ↓
                                                          ComparisonEngine
                                                                    ↓
                                                        GrowthStoryReporter
```

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

| Variant | Prompt | Knowledge | Phase | Expected Outcome |
|---------|--------|-----------|-------|-----------------|
| control | v0-naive | none | single | Baseline — model's built-in knowledge only |
| variant-a | v1-hardened | none | single | Prompt effect — structured execution adds value? |
| variant-b | v2-with-kb | targeted files | single | Knowledge effect — domain KB adds value? |
| variant-c | v2-with-kb | full tree (index.md) | single | Navigation effect — routing table + more KB? |
| variant-d | v3-explore/act | full tree (index.md) | two-phase | Consumption effect — structured reading adds value? |

**Ablation logic:**
- control → variant-a: isolates prompt improvement (∆ = execution structure)
- variant-a → variant-b: isolates knowledge addition (∆ = domain KB)
- variant-b → variant-c: isolates knowledge breadth (∆ = more KB + routing)
- variant-c → variant-d: isolates consumption pattern (∆ = explore/act phases)

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
