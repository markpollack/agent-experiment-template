# Session Journal: 2026-05-26 — Flywheel Wiring + Dependency Catch-Up

> **Project**: agent-experiment-template
> **Handoff from**: agento-forge session (flywheel codification)
> **Roadmap followed**: `~/projects/agento-forge/plans/flywheel-template/ROADMAP.md`

## What was accomplished

### 1. Flywheel Methodology Wiring (16 commits, 5 stages)

Wired the Improvement Flywheel methodology into the agent-experiment-template. The template already had the mechanical pieces (Markov scripts, variant configs, journal capture, GrowthStoryReporter) but no methodology connecting them.

**Stage 1 — Documentation (Steps 1.0–1.K)**
- Added Phase 0 (state taxonomy discovery), Improvement Methodology (5-step cycle, 7 loss dimensions, 5 levers, 5 loop types), and Variant Progression sections to README.md
- Added Methodology section to CLAUDE.md with build mode vs. optimize mode distinction

**Stage 2 — Configuration and Schema (Steps 2.0–2.K)**
- Added `iteration` field to `experiment-config.yaml` with `finding` + `hypothesis` per variant
- Added `IterationMetadata` nested record to `VariantSpec.java`
- Added YAML parsing in `ExperimentApp.loadConfig()`

**Stage 3 — Analysis and Reporting (Steps 3.0–3.K)**
- Added `write_interpretation()` to `make_markov_analysis.py` that writes `analysis/markov-interpretation.md` with loop amplification diagnostics, threshold-based classification, and intervention recommendations
- Enhanced `GrowthStoryReporter` with regression flagging and `appendIterationMotivation()` method
- Wired motivation into `runAllVariants()` loop

**Stage 4 — Template Updates (Steps 4.0–4.K)**
- Updated `VISION-TEMPLATE.md` with Improvement Methodology and Target Metrics sections
- Updated `DESIGN-TEMPLATE.md` with empirical variant motivation, iteration metadata pattern, and Measurement Strategy
- Rewrote `ROADMAP-TEMPLATE.md` Stage 2 around the flywheel cycle with Phase 0 taxonomy discovery

**Stage 5 — Validation (Step 5.1)**
- End-to-end consistency check, compile verification, vocabulary audit

### 2. Dependency Catch-Up to agentworks BOM 1.0.12

The template was pinned to stale SNAPSHOT dependencies with old groupIds. Updated to released versions:

| Dependency | Old | New |
|-----------|-----|-----|
| experiment-core | 0.1.0-SNAPSHOT | 0.2.0 |
| agent-judge-core/exec | org.springaicommunity 0.9.1-SNAPSHOT | io.github.markpollack 0.11.0 |
| agent-client | org.springaicommunity.agents/spring-ai-agent-client 0.10.0-SNAPSHOT | io.github.markpollack/agent-client-core 0.18.0 |
| claude-agent | org.springaicommunity.agents/spring-ai-claude-agent 0.10.0-SNAPSHOT | io.github.markpollack/agent-claude 0.18.0 |
| claude-code-sdk | org.springaicommunity 1.0.0-SNAPSHOT | io.github.markpollack 1.1.0 |
| journal-core + claude-code-capture | 0.1.0-SNAPSHOT | 1.2.0 |
| workflow-flows | 0.6.0-SNAPSHOT | 0.6.0 |

Also fixed `ExperimentRunner` → `AgentExperiment` class rename and all `org.springaicommunity.*` → `io.github.markpollack.*` Java imports.

**`./mvnw compile` now passes cleanly.**

### 3. Experiment-Driver Docs Update (in ~/projects/docs)

Added flywheel methodology and template references to the experiment-driver documentation:
- `getting-started.mdx` — Quick Start with Template section
- `creating-experiments.mdx` — Improvement Flywheel section (IterationMetadata, intervention levers, comparison reporting)
- `diagnostic-reasoning.mdx` — Behavioral Diagnostics section (Markov loop amplification, loop types, interpretation output)

## Key files changed

### agent-experiment-template
| File | Change |
|------|--------|
| `pom.xml` | BOM-aligned versions, groupId migration |
| `README.md` | Phase 0, Improvement Methodology, Variant Progression |
| `CLAUDE.md` | Methodology references, build/optimize mode |
| `experiment-config.yaml` | `iteration` field per variant |
| `VariantSpec.java` | `IterationMetadata` record, `iteration` field |
| `ExperimentApp.java` | Parse iteration from YAML, AgentExperiment rename, imports |
| `GrowthStoryReporter.java` | `appendIterationMotivation()`, regression flagging |
| `JuryFactory.java` | Import migration |
| `TemplateAgentInvoker.java` | Javadoc import fix |
| `scripts/make_markov_analysis.py` | `write_interpretation()` for markov-interpretation.md |
| `plans/VISION-TEMPLATE.md` | Methodology + Target Metrics |
| `plans/DESIGN-TEMPLATE.md` | Iteration metadata, Measurement Strategy |
| `plans/ROADMAP-TEMPLATE.md` | Phase 0 discovery, flywheel-cycle Stage 2 |

### ~/projects/docs
| File | Change |
|------|--------|
| `docs/experiment-driver/getting-started.mdx` | Template quickstart |
| `docs/experiment-driver/creating-experiments.mdx` | Flywheel, IterationMetadata, comparison reporting |
| `docs/experiment-driver/diagnostic-reasoning.mdx` | Behavioral diagnostics, loop amplification |

## Decisions made

- **No backward compat shims** — template evolves freely, older experiments pin their own versions
- **IterationMetadata is a nested record** (not flat fields) — maps directly to YAML structure
- **`hypothesis` is required** even on baseline — every variant should declare what it tests
- **Amplification thresholds**: HIGH >= 2.0, moderate >= 1.5 — based on flywheel concept doc evidence
- **Pre-existing compile issues** were caused by stale SNAPSHOT dependencies, not code bugs

### 4. Merge Resolution and Push

Remote had 2 commits ahead (Java 21 bump, workflow-journal dependency, agent-client 0.15.0 intermediate). Merge conflict in pom.xml resolved: kept our BOM 1.0.12 versions, adopted workflow-journal dependency from remote.

Both repos pushed to origin/main:
- `agent-experiment-template` → `883b7a4..c6233c7` (19 commits + merge)
- `docs` → `4e76803..1afa65a` (1 commit)

## Repos touched

| Repo | Location | Branch | Pushed |
|------|----------|--------|--------|
| agent-experiment-template | `~/projects/agent-experiment-template` | main | Yes |
| docs | `~/projects/docs` | main | Yes |
| agento-forge | `~/projects/agento-forge` | — | Read-only (VISION, DESIGN, ROADMAP, flywheel concept) |

## What's next (from the original handoff)

- **Workstream 2**: Update `/forge-eval-agent` skill — plans at `~/projects/agento-forge/plans/flywheel-skill/`
- **Workstream 3**: Refresh agento-studio docs site — plans at `~/projects/agento-forge/plans/flywheel-docs/`
