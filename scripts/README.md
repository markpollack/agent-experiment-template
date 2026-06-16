# scripts/ — analysis layer policy: depend on `agent-control-theory`, don't copy

The reusable analysis — Markov chains, the absorbing-chain fundamental matrix, **Lyapunov**
dynamics, EXPLORE-quality, drift checks, validation, figures/diagrams/sankey, and the
`AgentControlJudge` — lives in the installable **`agent-control-theory`** library
(`~/projects/agent-control-theory`, package `agent_control_theory`; renamed from
markov-agent-analysis, which survives as a back-compat shim). **Import it; never re-vendor it.**

```bash
uv pip install -e ~/projects/agent-control-theory[all]   # or: pip install -e "~/projects/agent-control-theory[all]"
```

## What lives here vs. in the library

| Concern | Where it lives | Notes |
|---------|----------------|-------|
| State taxonomy (`classify_state`) | **here** (`make_markov_analysis.py`) | per-experiment domain glue — injected as the pipeline's `classify_fn` |
| Markov / Lyapunov / EXPLORE-quality / drift / validation | **library** | `MarkovAnalysisPipeline`, `build_absorbing_chain_from_traces`, `lyapunov_table`/`lyapunov_values`/`drift_check`, `run_second_order_test`/`run_stationarity_test`, the `explore_quality` functions |
| Figures / diagrams / sankey | **library** (`agent_control_theory.figures` …) | `make_figures.py` here is a thin stub for *domain-specific* plots only |
| Result ETL (session JSON → parquet) | **here** (`load_results.py`) | experiment-specific result layout; the library's `load_trace_jsonl` reads JSONL traces, a different input |

## The rule

A script in this directory is justified only if it is **domain glue** — the `classify_state`
taxonomy, the result-layout ETL, or a short driver that wires the library's functions. If you
find yourself copying analysis logic (transition math, Lyapunov, figure helpers) into a script
here, stop: that logic belongs in `agent-control-theory`. Fix or extend the library instead, then
import it. The template's `make_markov_analysis.py` already imports the library — keep new work
on that side of the line.
