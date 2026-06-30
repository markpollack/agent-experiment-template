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
| Trace ETL (canonical journal → DataFrames) | **library** (`agent_control_theory.load_journal`) | reads the on-by-default journal (`events.jsonl` + `analysis.jsonl`) under `results/` and returns `(tool_uses_df, item_results_df)` with per-tool cost. **The trace source of truth** — `make_markov_analysis.py` calls it directly |
| ~~Result ETL (session JSON → parquet)~~ | ~~`load_results.py`~~ **deprecated** | legacy result-store path; kept only for **pre-journal** data (no per-tool cost). New experiments use `load_journal`, not this |

## The rule

A script in this directory is justified only if it is **domain glue** — the `classify_state`
taxonomy or a short driver that wires the library's functions. The trace ETL is **not** glue:
reading the canonical journal is `agent_control_theory.load_journal` (`make_markov_analysis.py`
calls it directly). `load_results.py` is the **deprecated** result-store reader, kept only for
pre-journal data. If you find yourself copying analysis logic (transition math, Lyapunov, figure
helpers, trace loading) into a script here, stop: that logic belongs in `agent-control-theory`.
Fix or extend the library instead, then import it. The template's `make_markov_analysis.py` already
imports the library — keep new work on that side of the line.

### Cost is an allocation, not a measurement

Per-tool cost (`attributed_cost_usd`) is **inferred after the run** — total run cost split
output-token-proportionally across turns, even-split within a turn, blended-model-priced. It is an
allocation, not a wire-measured per-tool charge. Every cost-weighted output must say so and carry
its `attribution_method`: `OUTPUT_TOKEN_PROPORTIONAL` is the precise split; `EVEN_SPLIT` flags the
coarse fallback (no per-turn tokens). Filter or down-weight `EVEN_SPLIT` runs from the data alone —
`load_journal` surfaces the method per row.
