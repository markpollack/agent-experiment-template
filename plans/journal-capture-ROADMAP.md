# Roadmap: journal-capture (slice 3 of 5) — canonical journal on-by-default in the template

> **Created**: 2026-06-30T12:57-04:00
> **Last updated**: 2026-06-30T12:57-04:00
> **Design**: thin pointer `plans/journal-capture-DESIGN.md` → canonical contract
> `~/projects/agent-journal/plans/journal-capture-DESIGN.md` (§4 frozen, §6 guarantee #3)
> **Branch**: `feat/journal-capture-slice-3`

## Overview

Make the **canonical agent-journal capture on-by-default** for every experiment bootstrapped from this
template — DESIGN §6 guarantee #3 ("on-by-default in the template — every future experiment inherits
it"), the belt-and-suspenders to the framework fix (experiment-core slice 2). A new experiment must
never start in the broken result-store-only shape v3/v4 were in.

Because experiment-core (slice 2) makes journaling a **property of running an experiment** (default-on
when an `outputDir` is configured), and this template **already** wired `outputDir(results)`, the
behaviour came for free once the SNAPSHOT deps were picked up. The author writes **zero journal code**.
The slice is therefore: consume the SNAPSHOTs, make the default **visible**, **guard** it with a
committed regression test, and **repoint the analysis-layer guidance** off the retired result-store
ETL (`load_results.py`) onto the canonical journal (`load_journal`), with the allocation-not-measurement
cost caveat.

Built **SNAPSHOT-first** (DESIGN §9/A3) against agent-journal `1.6.0-SNAPSHOT` (slice 1) +
experiment-core `0.6.0-SNAPSHOT` (slice 2), both installed to `~/.m2`.

> **Before every commit**: verify ALL exit criteria for the current step are met. Build with the
> wrapper (`./mvnw`). No Claude attribution / no "tuvium".

## Status at a glance

| Stage | What | State |
|-------|------|-------|
| S0 | Gate: slice-1 + slice-2 SNAPSHOTs resolve | ✅ done |
| S1 | Consume SNAPSHOTs (pom bump) + visible on-by-default wiring | ✅ done |
| S2 | Committed smoke / regression guard (`JournalCaptureSmokeTest`) | ✅ done |
| S3 | Repoint template docs → canonical journal ETL; retire result-store steering | ✅ done |
| S4 | QA review + consolidation (DESIGN pointer, roadmap, learnings) | ✅ done |

---

## Stage S0 — Dependency gate

### Step S0.1: Confirm the frozen interfaces resolve before building

**Entry criteria**:
- [x] Read: canonical `journal-capture-DESIGN.md` (§4 frozen contract, §6 guarantee #3, A4 dir, A5 header)
- [x] Read: `plans/inbox/journal-capture-handoff.md` (this slice, scoped)

**Work items**:
- [x] VERIFY agent-journal `1.6.0-SNAPSHOT` (slice 1: eager `stepCosts()`, production `RunRecorder`,
  A5 header) installed in `~/.m2` (`journal-core`, `claude-code-capture`).
- [x] VERIFY experiment-core `0.6.0-SNAPSHOT` (slice 2: `AgentExperiment` owns the run-journal
  lifecycle, journaling DEFAULT-ON, A4 layout, `run.json` carries `config.{variant,itemId,...}`)
  installed in `~/.m2` — built from the feature branch (jar dated 2026-06-28).
- [x] READ the slice-2 surface (`ExperimentConfig.shouldJournal()`, `AgentExperiment.openExperimentJournal`,
  `ExperimentJournal`) to confirm: on-by-default, **needs `outputDir`** else WARN + no-op.

**Exit criteria**:
- [x] Both SNAPSHOTs resolve; closure is consistent (experiment-core 0.6.0-SNAPSHOT pulls
  journal-core/claude-code-capture 1.6.0-SNAPSHOT).
- [x] Confirmed the only template-side precondition is a configured `outputDir`.

**Deliverables**: a verified dependency gate (DESIGN §5 row 3 depends on slices 1 + 2).

---

## Stage S1 — Consume SNAPSHOTs + visible on-by-default wiring

### Step S1.1: pom bump + make the journal default legible

**Entry criteria**:
- [x] S0.1 complete

**Work items**:
- [x] BUMP `pom.xml`: `experiment-core` 0.5.0 → `0.6.0-SNAPSHOT`, `journal` 1.4.0 → `1.6.0-SNAPSHOT`,
  with a SNAPSHOT-first comment (DESIGN A3). `experiment-workflow` already `0.6.0-SNAPSHOT`.
- [x] DOCUMENT the default at the wiring site: a comment at `ExperimentApp.runVariant`'s
  `.outputDir(results)` explains it enables the canonical journal (events + per-tool `StepCostEvent`),
  the on-disk layout, that the AgentInvoker writes **zero** journal code, and the `withoutJournal()`
  opt-out for judge-only runs.
- [x] CONFIRM no journal code is added to any invoker — the default is inherited from experiment-core.

**Exit criteria**:
- [x] `./mvnw -DskipTests compile` green against the SNAPSHOTs.
- [x] The on-by-default journal is discoverable by a bootstrapper reading `ExperimentApp` + `CLAUDE.md`.

**Deliverables**: the template consumes the lifecycle; the default is visible, not accidental.

---

## Stage S2 — Regression guard

### Step S2.1: committed smoke test — fresh experiment writes a canonical journal, no author journal code

**Entry criteria**:
- [x] S1.1 complete

**Work items**:
- [x] ADD `src/test/java/com/example/experiment/JournalCaptureSmokeTest.java`: drives the template's
  **real** `ExperimentApp.runVariant` wiring (its `ExperimentConfig` incl. `outputDir`) with a
  synthetic-phase `AgentInvoker` that returns only a `PhaseCapture` (two tool calls + per-turn usage)
  and **contains zero journal code**, over a minimal local filesystem dataset, with a passing jury
  (hermetic — no `mvn`, no network).
- [x] ASSERT a canonical `analysis.jsonl` appears under `results/` with the **A5 schema header**
  (`@type:header`, `schemaVersion:1`, `stream:analysis`) followed by two derived `step_cost` events
  keyed by tool_use id (`toolu_01`/`toolu_02`), each `OUTPUT_TOKEN_PROPORTIONAL` with
  `attributedCostUsd`; and an `events.jsonl` carrying the same tool ids.
- [x] RESET the process-global `Journal` context between tests (`@AfterEach Journal.reset()`).

**Exit criteria**:
- [x] `./mvnw test` green (1 test). This is the acceptance: **bootstrap → run → canonical journal
  present, author wrote zero journal code.**
- [x] The test fails if a future change drops `outputDir` / breaks the default — guarding the exact
  v3/v4 regression.

**Deliverables**: a permanent on-by-default guarantee in every bootstrapped project (ships with the template).

---

## Stage S3 — Repoint analysis-layer guidance onto the canonical journal

### Step S3.1: canonical journal = trace source of truth; retire result-store steering

**Entry criteria**:
- [x] S2.1 complete

**Work items**:
- [x] UPDATE the template guidance docs to teach the canonical journal:
  - `plans/DESIGN-TEMPLATE.md` — architecture diagram adds the journal branch + `load_journal`;
    Measurement Strategy gains the journal-as-truth note, a Cost row, and the allocation caveat.
  - `plans/ROADMAP-TEMPLATE.md` — MEASURE steps note the journal is captured automatically (no ETL
    step) and that cost is an allocation.
  - `plans/VISION-TEMPLATE.md` — Target Metrics gains cost-weighted `V(EXPLORE)`; a Traces & cost note.
  - `README.md` — "Analysis Scripts" rewritten to lead with the canonical journal + `load_journal`,
    with the allocation-not-measurement callout; `load_results.py` demoted to deprecated.
  - `scripts/README.md` — ETL row → `load_journal` (trace source of truth); `load_results.py` row
    struck through (deprecated); added the cost-allocation subsection.
  - `CLAUDE.md` — "What's Pre-Wired" records the on-by-default canonical journal.
- [x] DEPRECATE `scripts/load_results.py` — header banner pointing at `load_journal`, retained only
  for **pre-journal** result-store data (DESIGN §7); not deleted (back-compat) and not extended.
- [x] PIVOT `scripts/make_markov_analysis.py` `load_data()` to read the canonical journal via
  `agent_control_theory.load_journal(results/, require_cost=False)`, with the legacy parquet as a
  graceful fallback; docstring updated to name the journal as the data source.
- [x] ALIGN `scripts/setup_venv.sh` to the `agent-control-theory` library name (the README Setup now
  points there; the rename predated this slice but left the helper stale).

**Exit criteria**:
- [x] No template doc steers a new experiment to the result-store-only path; `load_results.py` is
  clearly the deprecated/legacy reader.
- [x] The documented analysis flow and `make_markov_analysis.py` both source from the canonical journal.

**Deliverables**: the analysis-layer guidance matches the on-by-default reality.

---

## Stage S4 — QA review + consolidation

### Step S4.1: design pointer, roadmap, learnings, self-review

**Entry criteria**:
- [x] S1–S3 complete

**Work items**:
- [x] WRITE `plans/journal-capture-DESIGN.md` — thin pointer to the canonical contract; records that
  this repo's template "design" lives in `CLAUDE.md` + the `*-TEMPLATE.md` scaffolds (this repo has no
  standalone `plans/DESIGN.md`), and lists the slice's touch-points.
- [x] WRITE this `plans/journal-capture-ROADMAP.md` (Forge style — stages/steps, entry/exit, QA loop).
- [x] CAPTURE `plans/learnings/journal-capture-slice-3.md`.
- [x] SELF-REVIEW against acceptance + the §4 rows this slice touches; surface any contract change
  (none found) in the handoff report.

**Exit criteria**:
- [x] Acceptance demonstrably met; `./mvnw test` green; zero MUST-FIX from self-review.
- [x] Design ↔ roadmap coupled and current.

**Deliverables**: a reviewed, consolidated, documented slice.

---

## Acceptance (DESIGN §8, template row)

- [x] Bootstrap a throwaway experiment from the template → run it → a canonical journal
  (`analysis.jsonl` with `StepCostEvent` + A5 header) appears — **author wrote zero journal code**.
  (Demonstrated hermetically by `JournalCaptureSmokeTest`, which drives the template's own
  `ExperimentApp` wiring.)
- [x] Template docs no longer steer new experiments toward the result-store-only path.

## QA review log

| Date | Reviewer | MUST FIX | Outcome |
|------|----------|----------|---------|
| 2026-06-30 | self-review (steward) | none | Acceptance met: `./mvnw test` green; on-by-default journal proven by `JournalCaptureSmokeTest`; result-store steering retired across README / scripts / templates / CLAUDE.md. No contract change surfaced (§6 #3 satisfied without new template wiring; A4 glob + A5 header confirmed on real output). Folds into the single coordinated release (A3). |

## Post-slice dependency alignment (agentworks-bom 1.15.0)

The template caught up to the latest suite BOM. agent-journal's slice-1 primitives ship as the
RELEASED `journal-core` / `claude-code-capture` `1.6.0`, so those moved **off SNAPSHOT**
(`journal.version` → `1.6.0`); `agent-client` tracked to `0.25.0` (BOM 1.15.0's Boot-4 auto-config
registration fix — a no-op for this plain-Java CLI, taken for suite alignment); `agent-judge 0.13.0`
/ `workflow 0.10.0` / `claude-code-sdk 1.4.0` already matched.

`experiment-core` / `experiment-workflow` stay on `0.6.0-SNAPSHOT`: agent-experiment's slice-2
`0.6.0` (the run-journal lifecycle) is on its `main` but **not released**, and the BOM still pins
`experiment-core 0.5.0` (pre-slice-2). That is the **only** remaining SNAPSHOT surface, and by
decision (2026-07-01) it stays until the agent-experiment `0.6.0` release is cut — which is **batched
until all scheduled agent-experiment work is complete** (Central release overhead), not cut early.
Verified: `./mvnw dependency:tree` resolves journal `1.6.0` + agent-client `0.25.0` (releases), no
SNAPSHOT leak beyond experiment-core/-workflow; `./mvnw test` green.

## Conventions

- **Every step** ends green (`./mvnw test`) and updates this file's checkboxes.
- **Learnings** are a primary artifact (`plans/learnings/`).
- **SNAPSHOT-first** (DESIGN §9/A3): no per-component release mid-feature; the pom de-SNAPSHOTs each
  component as its release lands in the BOM (journal done; experiment-core pending).
- The canonical `journal-capture-DESIGN.md` is **READ-ONLY** here; contract changes are surfaced to
  the owner, not edited in.

## Revision History

| Timestamp | Change | Trigger |
|-----------|--------|---------|
| 2026-06-30T12:57-04:00 | Initial roadmap — S0–S4 done; acceptance met | Slice 3 implemented this session |
| 2026-07-01T13:41-04:00 | Catch up to agentworks-bom 1.15.0: journal → released 1.6.0, agent-client → 0.25.0; experiment-core/-workflow stay 0.6.0-SNAPSHOT (agent-experiment 0.6.0 release batched until its scheduled work is complete) | New BOM available; general template↔agent-experiment sync |
