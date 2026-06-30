# Vision: {{PROJECT_NAME}}

## Problem Statement

_What problem does this agent experiment solve?_

## Hypothesis

_What do you expect to learn from running this experiment?_

## Success Criteria

_How will you know the experiment succeeded?_

- [ ] Agent achieves target metric on benchmark dataset
- [ ] Knowledge ablation shows measurable improvement
- [ ] Growth story demonstrates progressive improvement across variants

## Improvement Methodology

This experiment follows the [Improvement Flywheel](https://github.com/markpollack/agento-forge/blob/main/concepts/improvement-flywheel.md) — a loss-driven cycle: RUN → MEASURE → DIAGNOSE → INTERVENE → VERIFY. Variants are empirically motivated by the previous variant's analysis.

**Loss dimensions most relevant to this experiment:**

_List 2-4 loss dimensions from the flywheel taxonomy that apply to your domain:_
- _e.g., Outcome loss — task failure rate_
- _e.g., Behavioral loss — fix loops from build failures_
- _e.g., Knowledge loss — repeated search for framework patterns_

## Target Metrics

_Define what "better" means for this experiment:_

| Metric | Baseline target | Goal | How measured |
|--------|----------------|------|-------------|
| _Pass rate_ | _> 50%_ | _> 80%_ | _BuildSuccessJudge_ |
| _Fix loop amplification_ | _< 3.0_ | _< 1.5_ | _Markov analysis (canonical journal)_ |
| _Domain score_ | _> 0.5_ | _> 0.8_ | _{{Domain}}Judge_ |
| _Cost-weighted V(EXPLORE)_ | _TBD_ | _↓_ | _load_journal → cost_weighted_explore (allocation)_ |

> **Traces & cost.** Every run writes a canonical agent-journal (`events.jsonl` + `analysis.jsonl`)
> on-by-default — the trace source of truth the analysis layer reads via `load_journal`. Per-tool
> cost is an **allocation** (output-token-proportional), not a wire measurement; it carries an
> `attribution_method` and must be reported as such.

## Scope

**In scope:**
- _List what this experiment covers_

**Out of scope:**
- _List what this experiment does NOT cover_
