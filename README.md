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

## Next Steps

1. **Edit prompts** — Start with `prompts/v1-hardened.txt`. Add domain-specific instructions for your task.
2. **Add knowledge files** — Write guidance in `knowledge/domain/`. Reference them from `knowledge/index.md`.
3. **Add more repos** — Edit `dataset/items.yaml` to include repos that exercise different aspects of your task.
4. **Add custom judges** — Implement domain-specific judges beyond "does it build?" in `JuryFactory`.
5. **Customize the agent** — Edit the `AgentInvoker` class to change how the agent is invoked.

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

After running experiments, use the Python scripts in `scripts/` to analyze results:

```bash
# 1. Load results into parquet (run from project root)
python scripts/load_results.py --experiment my-experiment

# 2. Generate variant comparison figures
python scripts/make_figures.py

# 3. Run Markov chain analysis (optional, requires markov-agent-analysis library)
python scripts/make_markov_analysis.py
```

### Setup

```bash
# Option A: standard venv
./scripts/setup_venv.sh /path/to/markov-agent-analysis

# Option B: uv (recommended if available)
uv venv scripts/.venv
uv pip install -r scripts/requirements.txt
uv pip install -e /path/to/markov-agent-analysis[all]
```

### Customize

Each script has a `# CUSTOMIZE` section at the top:
- `load_results.py`: Update `SCORE_MAP` with your judge class names
- `make_markov_analysis.py`: Update `STATES` list and `classify_state()` with your domain's tool-call taxonomy
- `make_figures.py`: Update `VARIANT_ORDER` and add domain-specific figures

### Output

| Script | Output |
|--------|--------|
| `load_results.py` | `data/curated/*.parquet` — 4 tables: runs, item_results, tool_uses, judge_details |
| `make_figures.py` | `docs/figures/*.pdf + *.png` — pass rate, cost/quality, per-item breakdown |
| `make_markov_analysis.py` | `docs/figures/*.pdf + *.png` — transition matrices, fundamental matrix, loop amplification, Sankey flows |

## Requirements

- Java 17+
- Maven (wrapper included)
- `ANTHROPIC_API_KEY` environment variable
- Python 3.11+ (for analysis scripts)
