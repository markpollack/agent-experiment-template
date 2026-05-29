# Agent Experiment Template

Standard template for agent experiments with pre-wired experiment loop. Used by `markpollack/forge` (Loopy's `/forge-agent`) to scaffold new experiment projects.

## What's Pre-Wired

- `ExperimentApp` — Full CLI with `--variant`, `--item`, `--run-all-variants`, `--project-root`
- `ExperimentVariantConfig` — Top-level config loaded from experiment-config.yaml, with item filtering
- `VariantSpec` — Per-variant specification with two-phase support (`actPromptFile`, `isTwoPhase()`)
- `AbstractTemplateAgentInvoker` — Template-method base with pre/post hooks and knowledge injection
- `TemplateAgentInvoker` — Single-phase placeholder (rename to `{Domain}AgentInvoker`)
- `TwoPhaseTemplateAgentInvoker` — Two-phase (explore + act) placeholder
- `WorkflowAgentInvoker` — Single-step workflow with trace capture via `AgentClientStep` + `ClaudeAgentModel` (extends `AbstractTemplateAgentInvoker`). Preferred over `ClaudeStep` for experiments — produces JSONL trace files with full tool-call data for Markov analysis.
- `WorkflowInvoker<S>` — Multi-step typed workflow base with journal + cost tracking (implement `buildWorkflow`/`buildInitialState`)
- `SlugFilteringDatasetManager` — Single-item smoke testing via `--item`
- `JuryFactory` — Builds CascadedJury with tier-0 BuildSuccessJudge pre-wired
- `GrowthStoryReporter` — Variant comparison → markdown growth story

## What You Customize (3 Pluggable Pieces)

1. **AgentInvoker** — Rename `TemplateAgentInvoker` to `{Domain}AgentInvoker`, override `preInvoke`/`invokeAgent`/`postInvoke`
2. **Custom Judges** — Implement domain-specific judges for tiers 1-3
3. **Knowledge Files** — Write domain knowledge in `knowledge/domain/`

## Directory Structure

```
├── experiment-config.yaml      # Top-level config with variant specs
├── dataset/items.yaml          # Benchmark dataset items
├── knowledge/
│   ├── index.md                # Knowledge routing table (JIT navigation)
│   └── domain/                 # Domain-specific knowledge files
├── prompts/
│   ├── v0-naive.txt            # Minimal control prompt
│   ├── v1-hardened.txt         # Structured execution prompt
│   └── v2-with-kb.txt          # KB-aware prompt
├── results/                    # Experiment results (generated)
└── plans/                      # VISION, DESIGN, ROADMAP templates
```

## Running

```bash
./mvnw compile exec:java -Dexec.args="--variant control"
./mvnw compile exec:java -Dexec.args="--variant control --item example-project"
./mvnw compile exec:java -Dexec.args="--run-all-variants"
```

## Methodology

This template implements the **Improvement Flywheel** — a loss-driven method for iterative agent improvement. The canonical reference is [`improvement-flywheel.md`](https://github.com/markpollack/agento-forge/blob/main/concepts/improvement-flywheel.md) in agento-forge.

Key concepts:
- **Cycle**: RUN → MEASURE → DIAGNOSE → INTERVENE → VERIFY
- **7 loss dimensions**: outcome, behavioral, knowledge, tooling, evaluation, stability, regression
- **5 intervention levers**: prompt, knowledge/skills, execution structure, model, rubric
- **Loop types**: productive, friction, failure, diagnostic, degenerate
- **Variants are empirically motivated** — each exists because the previous variant's analysis revealed a specific gap

### Build Mode vs. Optimize Mode

**Build mode**: Adding infrastructure — new judges, agent invoker customization, dataset expansion, knowledge file scaffolding. This is structural work on the experiment harness.

**Optimize mode**: Running the improvement flywheel — executing variants, measuring loss signals, diagnosing gaps, intervening with targeted changes, and verifying deltas. This is iterative work on agent quality.

When in optimize mode, follow the flywheel cycle strictly: don't skip DIAGNOSE (jumping from MEASURE to INTERVENE), don't skip VERIFY (moving to the next iteration without confirming the fix worked), and record every variant's finding and hypothesis in `experiment-config.yaml`.

## Dependencies

- `experiment-core` (ai.tuvium) — ExperimentRunner, ComparisonEngine, ResultStore, SessionStore
- `agent-judge-core` + `agent-judge-exec` — Judge, Jury, CascadedJury, BuildSuccessJudge
- `spring-ai-agent-client` + `spring-ai-claude-agent` — Single-phase agent invocation
- `claude-code-sdk` — Two-phase session support (ClaudeSyncClient)
- `journal-core` + `claude-code-capture` — Phase capture and session log parsing
- `workflow-journal` — Journal integration for workflow step tracing
- `javaparser-core` — AST analysis for custom judges
