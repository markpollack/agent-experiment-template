# Roadmap: {{PROJECT_NAME}}

> **Created**: {{DATETIME}}
> **Status**: Not started

## Overview

Implementation roadmap for the {{PROJECT_NAME}} experiment.

---

## Stage 1: Project Setup

### Step 1.0: Design Review

**Entry criteria**:
- [ ] Read: `plans/VISION-TEMPLATE.md`
- [ ] Read: `plans/DESIGN-TEMPLATE.md`

**Work items**:
- [ ] REVIEW design for completeness
- [ ] FILL IN domain-specific sections
- [ ] RENAME templates to remove `-TEMPLATE` suffix

**Exit criteria**:
- [ ] VISION.md and DESIGN.md populated with domain content
- [ ] Create: `plans/learnings/step-1.0-design-review.md`
- [ ] COMMIT

### Step 1.1: Implement AgentInvoker

**Entry criteria**:
- [ ] Step 1.0 complete

**Work items**:
- [ ] RENAME `TemplateAgentInvoker` to `{{Domain}}AgentInvoker`
- [ ] IMPLEMENT domain-specific agent invocation logic
- [ ] WIRE UP AgentClient with appropriate model

**Exit criteria**:
- [ ] AgentInvoker compiles and passes basic test
- [ ] Create: `plans/learnings/step-1.1-agent-invoker.md`
- [ ] COMMIT

### Step 1.2: Configure Judges

**Entry criteria**:
- [ ] Step 1.1 complete

**Work items**:
- [ ] CONFIGURE deterministic judges (build, preservation)
- [ ] IMPLEMENT domain-specific judges (if any)
- [ ] WIRE UP JuryFactory with correct tier policies

**Exit criteria**:
- [ ] Jury builds and judges a mock context
- [ ] Create: `plans/learnings/step-1.2-judges.md`
- [ ] COMMIT

### Step 1.3: Populate Dataset

**Entry criteria**:
- [ ] Step 1.2 complete

**Work items**:
- [ ] POPULATE `dataset/items.yaml` with benchmark items
- [ ] VERIFY each dataset item builds and tests pass
- [ ] CONFIGURE workspace materialization

**Exit criteria**:
- [ ] All dataset items resolve and build
- [ ] Create: `plans/learnings/step-1.3-dataset.md`
- [ ] COMMIT

---

## Stage 2: Improvement Flywheel

### Step 2.0: Phase 0 — State Taxonomy Discovery

**Entry criteria**:
- [ ] Stage 1 complete — agent runs and produces results

**Work items**:
- [ ] RUN control variant 3–5 times to generate tool-call data
- [ ] RUN discovery mode: `MARKOV_DISCOVERY=true python scripts/make_markov_analysis.py`
- [ ] INSPECT clusters — identify related tool calls representing coherent activities
- [ ] DEFINE state taxonomy — name the clusters (verbs, 5–12 states, diagnostic value)
- [ ] CONFIGURE `classify_state()` in `make_markov_analysis.py`
- [ ] DEFINE cluster groups (productive, friction, knowledge access)

**Exit criteria**:
- [ ] `classify_state()` produces coherent transition matrices
- [ ] Cluster groups defined
- [ ] Create: `plans/learnings/step-2.0-taxonomy.md`
- [ ] COMMIT

### Step 2.1: Baseline (control)

**Entry criteria**:
- [ ] Step 2.0 complete

**Work items**:
- [ ] WRITE control prompt (`prompts/v0-naive.txt`)
- [ ] RUN: `--variant control`
- [ ] MEASURE: run `make_markov_analysis.py` and review `analysis/markov-interpretation.md`
- [ ] DIAGNOSE: identify dominant loss dimension from amplification and scores
- [ ] RECORD iteration metadata in `experiment-config.yaml` (finding: null, hypothesis)

**Exit criteria**:
- [ ] Baseline scores and Markov analysis captured
- [ ] Dominant loss dimension identified for next variant
- [ ] Create: `plans/learnings/step-2.1-baseline.md`
- [ ] COMMIT

### Step 2.2: Iteration 1 (variant-a)

**Entry criteria**:
- [ ] Step 2.1 complete — baseline diagnosis identifies target loss

**Work items**:
- [ ] INTERVENE: create prompt/knowledge targeting the diagnosed loss (choose lever)
- [ ] RUN: `--variant variant-a`
- [ ] VERIFY: compare against baseline — did the targeted loss decrease?
- [ ] CHECK for regressions in growth story
- [ ] RECORD iteration metadata (finding from baseline, hypothesis, delta)

**Exit criteria**:
- [ ] Comparison report shows delta for targeted dimension
- [ ] No unaddressed regressions
- [ ] Create: `plans/learnings/step-2.2-iteration1.md`
- [ ] COMMIT

### Step 2.N: Further Iterations

Repeat the flywheel cycle for each subsequent variant:
1. **DIAGNOSE** the latest variant's remaining loss
2. **INTERVENE** with the appropriate lever
3. **VERIFY** the delta and check for regressions
4. **RECORD** iteration metadata

### Step 2.K: Stage 2 Consolidation

**Work items**:
- [ ] RUN `--run-all-variants` for final comparison
- [ ] REVIEW `analysis/comparison-report.md` for overall progression
- [ ] REVIEW `analysis/markov-interpretation.md` for behavioral improvement
- [ ] COMPACT learnings — what worked, what regressed, what lever was most effective

**Exit criteria**:
- [ ] Growth story shows variant progression with iteration motivation
- [ ] Create: `plans/learnings/step-2.K-results.md`
- [ ] COMMIT
