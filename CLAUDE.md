# Agent Experiment Template

Standard template for agent experiments with pre-wired experiment loop. Used by `markpollack/forge` (Loopy's `/forge-agent`) to scaffold new experiment projects.

## What's Pre-Wired

- `ExperimentApp` — Full CLI with `--variant`, `--item`, `--run-all-variants`, `--project-root`
- `ExperimentVariantConfig` — Top-level config loaded from experiment-config.yaml, with item filtering
- `VariantSpec` — Per-variant specification with two-phase support (`actPromptFile`, `isTwoPhase()`)
- `AbstractTemplateAgentInvoker` — Template-method base with pre/post hooks and knowledge injection
- `TemplateAgentInvoker` — Single-phase placeholder (rename to `{Domain}AgentInvoker`)
- `TwoPhaseTemplateAgentInvoker` — Two-phase (explore + act) placeholder
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

## Dependencies

- `experiment-core` (ai.tuvium) — ExperimentRunner, ComparisonEngine, ResultStore, SessionStore
- `agent-judge-core` + `agent-judge-exec` — Judge, Jury, CascadedJury, BuildSuccessJudge
- `spring-ai-agent-client` + `spring-ai-claude-agent` — Single-phase agent invocation
- `claude-code-sdk` — Two-phase session support (ClaudeSyncClient)
- `journal-core` + `claude-code-capture` — Phase capture and session log parsing
- `javaparser-core` — AST analysis for custom judges
