# Gap: ClaudeAgentModel.traceDir() not set — no Claude Code JSONL traces

> **Filed**: 2026-06-03
> **Source**: weekly-kb-sync journal instrumentation — discovered during pre-Wave-5 Markov discovery prep
> **Severity**: High — Markov analysis requires Claude Code tool-call traces; without traceDir, none are written

## Problem

`ExperimentApp.buildAgentClient()` creates a `ClaudeAgentModel` without setting `.traceDir(path)`. This means every `call()` to Claude Code runs normally but writes zero JSONL trace files. The tool-call exhaust (Read, Write, Bash, Edit, Grep, etc.) is lost.

The `ClaudeAgentModel.traceDir` feature writes one JSONL file per invocation containing:
- `tool_use` events (name, id)
- `tool_result` events (id, isError, contentLength)
- `text` and `thinking` events
- `result` summary (tokens, cost, turns, duration)

This is the canonical Markov input — `make_markov_analysis.py` consumes these traces via `load_results.py`.

## Fix

In `ExperimentApp.main()`, compute a trace directory from the run root and pass it to the builder:

```java
Path traceDir = resolvedRunRoot.resolve("results/.traces");

ClaudeAgentModel agentModel = ClaudeAgentModel.builder()
        .timeout(Duration.ofMinutes(10))
        .defaultOptions(options)
        .traceDir(traceDir)       // <-- this is the missing line
        .build();
```

The trace directory should be co-located with results so `load_results.py` can find them. Each `call()` writes a separate JSONL file named by session ID.

## Relationship to journal-storage-not-configured

That issue (filed 2026-05-28) covers `Journal.configure()` for step-level journal events. This issue covers `traceDir` for Claude Code CLI tool-call traces. They are complementary:
- `Journal.configure()` → step transitions via WorkflowJournal
- `traceDir` → raw Claude Code tool exhaust per invocation

Both are needed for complete Markov analysis.

## Applied in weekly-kb-sync

The fix was applied in `weekly-kb-sync/ExperimentApp.java` on 2026-06-03. The trace dir resolves to `runs/weekly-sync/{date}/traces/`. The template should adopt the same pattern.

---

**RESOLVED 2026-06-04**: `ClaudeAgentModel.builder()` in `WorkflowAgentInvoker.java` already carried `.traceDir(TRACE_DIR)` (the assumed defect site `ExperimentApp.buildAgentClient()` does not exist in this template — only one builder call repo-wide). Remaining gap closed: `TRACE_DIR` re-pointed `results/traces` → `experiments/traces` to match the bud-template convention and the standardized run layout. journal-core/claude-code-capture bumped 1.2.0 → 1.3.0 (TraceWriter tool-input capture + control-char escaping).
