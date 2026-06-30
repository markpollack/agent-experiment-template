# Agent Experiment Template

A ready-to-run project for measuring and improving AI coding agents. Run your agent against real code repos, see what passes and what fails, then iterate on your prompts and knowledge files until it works.

## Quick Start

```bash
# 1. Run a single prompt version against all repos
./mvnw compile exec:java -Dexec.args="--variant control"

# 2. See the results
./mvnw compile exec:java -Dexec.args="--summary"

# 3. Run a better prompt version
./mvnw compile exec:java -Dexec.args="--variant variant-a"

# 4. Compare the two runs
./mvnw compile exec:java -Dexec.args="--compare"

# 5. Run all prompt versions in sequence
./mvnw compile exec:java -Dexec.args="--run-all-variants"
```

**Tip:** Test with a single repo first to iterate fast:
```bash
./mvnw compile exec:java -Dexec.args="--variant control --item gs-rest-service"
```

## What's in This Project

```
├── experiment-config.yaml      # Which prompt versions to run and in what order
├── dataset/items.yaml          # Code repos your agent will work on
├── prompts/                    # Prompt files — one per version
│   ├── v0-naive.txt            # Minimal prompt (baseline)
│   ├── v1-hardened.txt         # Structured execution steps
│   └── v2-with-kb.txt          # References knowledge files
├── knowledge/                  # Domain knowledge files the agent can read
│   ├── index.md                # Routing table — tells the agent which file to read when
│   └── domain/                 # Your domain-specific guidance
├── results/                    # Raw results (generated after runs)
├── analysis/                   # Comparison reports (generated)
└── src/main/java/              # Experiment wiring (rarely needs editing)
```

## How It Works

Each "prompt version" (control, variant-a, variant-b) represents a different strategy for your agent. The control uses a bare-bones prompt. Variant-a adds structured execution steps. Variant-b adds domain knowledge files. You run each version against the same set of code repos and compare pass rates.

The experiment runner clones each repo into an isolated workspace, hands it to your agent with the prompt, then judges the result (by default: does `mvn clean test` pass?). Results are saved so you can compare across runs and see which changes actually helped.

## Phase 0: State Taxonomy Discovery

Before running the improvement cycle, you need a **state taxonomy** — named states that `classify_state()` in `make_markov_analysis.py` maps tool calls to. This taxonomy is domain-specific and must be discovered empirically.

### Bootstrap procedure

1. **Run control variant 3–5 times.** Generate enough tool-call data to see the agent's natural behavior patterns.
2. **Run discovery mode.** Use `MARKOV_DISCOVERY=true` to see raw tool name + target frequencies.
3. **Inspect clusters.** Look for related tool calls that represent a coherent activity.
4. **Define state taxonomy.** Name the clusters. Each state should represent a distinct *kind of work* the agent does: exploring, building, fixing, verifying, searching, reading knowledge.
5. **Configure classifier.** Write `classify_state()` to map tool calls to your states. Test by re-running Markov analysis in normal mode and verifying the transition matrix looks coherent.
6. **Define cluster groups.** Group states into higher-level categories: productive work (WRITE, BUILD, VERIFY), friction (FIX, SEARCH), knowledge access (READ_KB, READ_SKILL). These groups are what the analysis-to-action step operates on.

### What makes a good taxonomy

- **States are verbs, not nouns.** They describe what the agent is *doing*, not what it's *looking at*.
- **5–12 states.** Fewer than 5 hides important distinctions. More than 12 makes transition matrices unreadable.
- **States have diagnostic value.** Each state should tell you something about agent quality when its frequency changes.

## Improvement Methodology

This template implements the **Improvement Flywheel** — a loss-driven method for iteratively improving agent systems through measured behavioral deltas and targeted interventions. The full methodology is documented in [`improvement-flywheel.md`](https://github.com/markpollack/agento-forge/blob/main/concepts/improvement-flywheel.md).

### The cycle

```
1. RUN        — Execute variants and capture journals
2. MEASURE    — Compute scores, traces, behavioral metrics
3. DIAGNOSE   — Convert signals into hypotheses about causes
4. INTERVENE  — Change prompt, KB, tool, workflow, rubric, or template
5. VERIFY     — Re-run and compare deltas / check for regressions
```

Each iteration estimates where the system is failing, chooses the most promising improvement direction, applies an intervention, and measures whether the system moved in the intended direction.

### Loss signal taxonomy

The loss signal is multi-dimensional. Not every dimension matters for every iteration, but the full surface is:

| Loss dimension | What it measures | Example signal |
|----------------|-----------------|----------------|
| **Outcome** | Task failure or low judge score | 3 of 10 benchmark cases fail |
| **Behavioral** | Unnecessary exploration or loops | BUILD→FIX loop amplification 3.2 |
| **Knowledge** | Repeated search or oracle calls | Repeated fallback inspection (e.g., jar decompilation) |
| **Tooling** | Errors reachable from multiple paths | Same exception from 4 different states |
| **Evaluation** | Judge variance or malformed output | Non-JSON judge response 2/7 runs |
| **Stability** | Large run-to-run variance | Quality scores range 0.28–0.72 |
| **Regression** | One metric improves, another worsens | Batch score +0.4 but scheduling score −0.3 |

### Intervention levers

The type of loss determines which lever to pull:

| Lever | When to use | Example |
|-------|-------------|---------|
| **1. Prompt** | Diffuse waste, no dominant failure, agent doesn't know when it's done | Add structured execution steps, stopping condition |
| **2. Knowledge / skills** | Friction loops around a specific knowledge gap | Add domain recipe to `knowledge/domain/` |
| **3. Execution structure** | Loops around states that could be deterministic | Replace exploration with a template, pre-analysis script, or steering hook |
| **4. Model** | Agent fundamentally cannot perform the task | Switch to a more capable model |
| **5. Rubric / evaluation** | Judge variance, scores don't correlate with quality | Tighten criteria, add scoring anchors |

### Loop type classification

Not all loops are problems. Classify before intervening:

| Loop type | Pattern | Action |
|-----------|---------|--------|
| **Productive** | WRITE → VERIFY → FIX → VERIFY | Leave it alone |
| **Friction** | SEARCH → READ → SEARCH → READ | Add knowledge or routing |
| **Failure** | BUILD → FIX → BUILD → FIX (same error) | Change strategy, not retry count |
| **Diagnostic** | BUILD → ERROR → READ_LOG → FIX | Leave it alone |
| **Degenerate** | EXPLORE → EXPLORE → EXPLORE | The agent is stuck — intervene |

### The critical distinction

Knowledge can't fix a reasoning gap. Steering can't fix a knowledge gap. A better model can't fix either. **Diagnose which problem you have before you reach for a lever.**

## Variant Progression

Variants are **empirically motivated, not pre-planned**. Each exists because the previous variant's analysis revealed a specific gap.

```
v0: baseline (control)
    → Run, measure: identify dominant loss dimension

v1: address the dominant loss
    → Typically prompt improvement (Lever 1) — clearest signal first
    → Run, measure: did the loss decrease? What's the next loss?

v2: address the next loss
    → Typically knowledge injection (Lever 2) — domain files for remaining gaps

v3+: address remaining losses
    → Structural fixes (Lever 3), rubric tightening (Lever 5)
    → Each variant is motivated by the previous variant's measurement
```

Every variant records its motivation in `experiment-config.yaml`:

```yaml
variants:
  - name: control
    promptFile: v0-naive.txt
    iteration:
      finding: null            # baseline — no prior finding
      hypothesis: "Establish baseline agent behavior"

  - name: variant-a
    promptFile: v1-hardened.txt
    iteration:
      finding: "v0 BUILD→FIX loop amplification 3.2"
      hypothesis: "Structured execution steps reduce fix loops"
```

This creates an audit trail: for every variant you can trace back to the observation that motivated it and verify whether the hypothesis held.

## Next Steps

Follow the improvement cycle:

1. **Discover your state taxonomy** — Follow Phase 0 above to define states for your domain.
2. **Run the baseline** — `--variant control` against your dataset. Capture journals.
3. **Measure and diagnose** — Run analysis scripts, identify the dominant loss dimension.
4. **Intervene** — Create the next variant targeting the identified gap. Record the finding and hypothesis.
5. **Verify** — Re-run and compare. Check for regressions before moving to the next iteration.

For infrastructure customization:
- **Custom judges** — Implement domain-specific judges for tiers 1–3 in `JuryFactory`.
- **Agent invoker** — Rename `TemplateAgentInvoker` to `{Domain}AgentInvoker`, override hooks.
- **Knowledge files** — Write domain guidance in `knowledge/domain/`, update `knowledge/index.md`.

## CLI Reference

| Flag | Description |
|------|-------------|
| `--variant <name>` | Run a single prompt version |
| `--item <slug>` | Filter to a single repo (for fast iteration) |
| `--run-all-variants` | Run all prompt versions in sequence |
| `--summary` | Print results from the most recent run |
| `--compare` | Compare the two most recent runs side by side |
| `--project-root <path>` | Override project root directory |

## Analysis Scripts

### The trace source of truth: the canonical journal

Every run writes a **canonical agent-journal on by default** (you wire nothing — the framework owns it). Beside each run's results sits:

```
results/<exp>/sessions/<session>/<variant>/journal/experiments/<exp>/runs/<runId>/
  run.json        # config.{variant, itemId, itemSlug, model, session} — the join key
  events.jsonl    # immutable execution events (LLMCallEvent, ToolCallEvent, …)
  analysis.jsonl  # derived per-tool StepCostEvents, keyed by tool_use id
```

The analysis layer reads **this** schema — not a separate result-store ETL. The library `agent_control_theory.load_journal(results_dir)` discovers every run under `results/` and returns `(tool_uses_df, item_results_df)` with per-tool cost already joined. `make_markov_analysis.py` calls it for you.

> **Cost is an allocation, not a measurement.** Per-tool cost (`attributed_cost_usd`) is total run cost split output-token-proportionally across turns (even-split within a turn, blended-model-priced) — inferred after the run, not a wire-measured per-tool charge. Each row carries its `attribution_method`: `OUTPUT_TOKEN_PROPORTIONAL` (precise) vs `EVEN_SPLIT` (coarse fallback, no per-turn tokens). Filter/down-weight `EVEN_SPLIT` from the data alone.

```bash
# 1. Run a variant — the canonical journal is written automatically
./mvnw compile exec:java -Dexec.args="--variant control"

# 2. Markov chain analysis — reads the canonical journal via load_journal
python scripts/make_markov_analysis.py

# 3. Variant comparison figures
python scripts/make_figures.py
```

> `load_results.py` is the **deprecated** result-store reader — retained only for pre-journal data (it cannot recover per-tool cost). New experiments do not use it.

### Setup

```bash
# Option A: standard venv
./scripts/setup_venv.sh /path/to/agent-control-theory

# Option B: uv (recommended if available)
uv venv scripts/.venv
uv pip install -r scripts/requirements.txt
uv pip install -e /path/to/agent-control-theory[all]
```

### Customize

Each script has a `# CUSTOMIZE` section at the top:
- `make_markov_analysis.py`: Update `STATES` list and `classify_state()` with your domain's tool-call taxonomy
- `make_figures.py`: Update `VARIANT_ORDER` and add domain-specific figures

### Output

| Script | Output |
|--------|--------|
| `make_markov_analysis.py` | `docs/figures/*.pdf + *.png` — transition matrices, fundamental matrix, loop amplification, Sankey flows; `analysis/markov-interpretation.md` — flywheel diagnostics with intervention recommendations |
| `make_figures.py` | `docs/figures/*.pdf + *.png` — pass rate, cost/quality, per-item breakdown |
| `load_journal` (library) | in-memory `(tool_uses_df, item_results_df)` from the canonical journal — the ETL `make_markov_analysis.py` consumes |

## Requirements

- Java 17+
- Maven (wrapper included)
- `ANTHROPIC_API_KEY` environment variable
- Python 3.11+ (for analysis scripts)
