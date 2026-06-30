# journal-capture (slice 3) — design pointer

> **This is a thin pointer.** The canonical, cross-repo design + frozen interface contract for the
> first-class journal-capture feature is **owned elsewhere** and must not be re-derived here:
>
> **`~/projects/agent-journal/plans/journal-capture-DESIGN.md`** — esp. §2 (allocation-not-measurement),
> §4 (frozen cross-repo interface contract), §6 #3 (on-by-default in the template), §7 (migration /
> pre-1.12.0 back-compat), §10 (amendments: A1 `EVEN_SPLIT`, A4 dir convention, A5 schema header).

## agent-experiment-template's slice (3 of 5)

Make canonical journal capture **on-by-default** for every bootstrapped experiment — the
belt-and-suspenders to the framework fix. The design of this repo's slice is small by construction:
experiment-core (slice 2) makes journaling a property of *running an experiment* (default-on when an
`outputDir` is set), and this template already wires `outputDir(results)`, so the author writes **zero
journal code**. The slice consumes the SNAPSHOTs, makes the default *visible*, *guards* it with a test,
and *repoints* the analysis-layer guidance onto the canonical journal.

Unlike a Forge application project, this repo has **no standalone `plans/DESIGN.md`** — it is the
scaffold generator, so its "design" lives in:

- **`CLAUDE.md`** → *"What's Pre-Wired"* (the canonical-journal-on-by-default entry).
- **`plans/DESIGN-TEMPLATE.md`** → *Architecture* (journal branch) + *Measurement Strategy* (journal
  as trace source of truth; cost as allocation) — the design every bootstrapped project inherits.
- **`README.md`** → *Analysis Scripts* (canonical journal + `load_journal`; the allocation caveat).
- **`plans/journal-capture-ROADMAP.md`** → the Forge stages/steps that built it.

## What this slice wired (touch-points)

| Concern | Where |
|---|---|
| Consume slice-1/slice-2 SNAPSHOTs | `pom.xml` (`experiment-core` 0.6.0-SNAPSHOT, `journal` 1.6.0-SNAPSHOT) |
| Visible on-by-default journal | `ExperimentApp.runVariant` comment at `.outputDir(...)` |
| On-by-default regression guard | `src/test/java/com/example/experiment/JournalCaptureSmokeTest.java` |
| ETL repointed to canonical schema | `README.md`, `scripts/README.md`, `scripts/make_markov_analysis.py` |
| Result-store path retired | `scripts/load_results.py` (deprecated header), `setup_venv.sh` rename |
| Template scaffolds | `plans/{DESIGN,ROADMAP,VISION}-TEMPLATE.md`, `CLAUDE.md` |

## Contract amendments touching this slice

None raised here. This slice **consumes** the frozen §4 contract without changing it:

- **§6 guarantee #3 (on-by-default in the template)** — satisfied with **no new template wiring**:
  the pre-existing `outputDir(results)` + slice-2's default-on behaviour is sufficient. (Confirmed
  finding, not a contract change.)
- **A4 (dir convention + `run.json` join surface)** — CONSUMED. The observed on-disk layout for the
  template's always-session runs is
  `results/<exp>/sessions/<session>/<variant>/journal/experiments/<exp>/runs/<runId>/{run,events,analysis}.jsonl`;
  the ETL glob `**/journal/experiments/*/runs/*/analysis.jsonl` matches.
- **A5 (per-stream `schemaVersion` header)** — CONSUMED. The smoke test asserts the `@type:header`
  line precedes the `step_cost` events in `analysis.jsonl`.
