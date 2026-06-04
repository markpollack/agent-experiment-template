# Gap: Journal.configure() never called — traces lost on exit

> **Filed**: 2026-05-28
> **Source**: security-remediation-agent control run — journal traces were in-memory only, lost after process exit
> **Severity**: Critical — Markov analysis impossible without persisted journal data

## Problem

Even after the journal-wiring-gap was fixed (WorkflowJournal.forRun wired into WorkflowExecutor), `Journal.configure(new JsonFileStorage(path))` is never called anywhere in the template. The default storage is `InMemoryStorage`, which means all journal traces are lost when the JVM exits.

This breaks:
1. `make_markov_analysis.py` — needs journal JSONL files on disk
2. Post-hoc analysis of agent behavior
3. Reproducibility — can't inspect what the agent did after the fact

## Fix

In the template's `ExperimentApp.main()` or in `WorkflowAgentInvoker` static init:

```java
import io.github.markpollack.journal.storage.JsonFileStorage;

// Before any Journal.run() call:
Journal.configure(new JsonFileStorage(Path.of("results", ".agent-journal")));
```

This should be wired once in `ExperimentApp.main()` before any variant runs, not in each invoker's static init. The journal directory should be under `results/` so it's co-located with experiment output.

## Workaround

The security-remediation-agent project added `Journal.configure()` in `SecurityRemediationInvoker`'s static initializer. This works but belongs in the framework/template, not in each consumer.

---

**RESOLVED 2026-06-04**: `Journal.configure(new JsonFileStorage(JOURNAL_DIR))` added to `WorkflowAgentInvoker` static initializer (`JOURNAL_DIR = experiments/traces/.agent-journal`), ported from bud-agent-experiment-template. Previously defaulted to InMemoryStorage — journal events lost on JVM exit. journal.version 1.2.0 → 1.3.0.
