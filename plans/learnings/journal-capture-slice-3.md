# Learnings — journal-capture slice 3 (template: canonical journal on-by-default)

> 2026-06-30 · branch `feat/journal-capture-slice-3`

## What the slice turned out to be

The headline guarantee (DESIGN §6 #3, "on-by-default in the template") needed **no new wiring**. The
template already set `.outputDir(results)` in `ExperimentApp.runVariant`, and experiment-core slice 2
makes journaling default-on whenever an `outputDir` is configured. So the canonical journal began
persisting the moment the SNAPSHOT deps were picked up. The real work was: **pom bump → make the
default legible → guard it with a test → repoint the docs.** "Wired and visible" beat "wire it."

## What was non-obvious

- **The default is silent.** Journaling-on is implicit (it happens because `outputDir` is set, not
  because anything says "journal = on"). That is exactly the v3/v4 failure mode in reverse — easy to
  *accidentally remove* by dropping `outputDir`. Mitigations: a comment at the wiring site naming the
  consequence, a `CLAUDE.md` entry, and a committed regression test that fails if the default breaks.
- **`journalItem` runs before the jury votes.** In `AgentExperiment.runItem`, the journal is written
  right after `invoke`, before judging — so a canonical journal appears even when the build judge later
  fails. The smoke test exploits this (a passing jury is for hermeticity, not correctness) but it also
  means real failed runs are still fully journaled.
- **The shipped `dataset/items.yaml` is not what runs.** `FileSystemDatasetManager` reads
  `dataset/dataset.json` (schemaVersion 1) + per-item `item.json` + `before/` dirs — the YAML is a
  placeholder a bootstrapper replaces. The smoke test builds the real `dataset.json` shape.
- **Test the template's wiring, not experiment-core's.** experiment-core already has its own
  `AgentExperimentJournalTest`. The value of *this* repo's test is proving the template's
  `ExperimentApp` config-building (the `outputDir`) produces the journal — so the test drives
  `ExperimentApp.runVariant`, overriding only `createInvoker` (package-private) to inject a
  synthetic-phase invoker. That keeps "author wrote zero journal code" honest.
- **The `Journal` context is process-global.** `ExperimentJournal` save/restores it under a lock per
  run; tests must `Journal.reset()` between cases.

## What I deliberately did NOT do

- **Did not rewrite the Python analysis pipeline.** Pointing the full ETL at the canonical schema for
  a real experiment is slice 5 (v4 adopt). I pivoted `make_markov_analysis.py`'s `load_data()` to
  prefer `load_journal` (with a legacy-parquet fallback) and repointed all docs, but I cannot execute
  the Python here (no guaranteed venv with `agent-control-theory` + `duckdb`), so I kept the change
  fallback-preserving rather than shipping an unrun rewrite.
- **Did not delete `load_results.py`.** DESIGN §7 keeps pre-journal result-store data valid (step-count
  `V` + per-run cost); the script is deprecated and de-documented, not removed.

## Contract: no changes surfaced

This slice consumes the frozen §4 contract verbatim. §6 #3 is met without new template wiring; A4 glob
and A5 header confirmed on the smoke test's real output. Recorded in `plans/journal-capture-DESIGN.md`.
