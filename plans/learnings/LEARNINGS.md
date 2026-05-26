# Learnings

Compacted learnings from each stage of the flywheel wiring workstream.

## Stage 1: Methodology Documentation

**What was done**: Added flywheel methodology narrative to README.md and CLAUDE.md. No code changes.

**Key decisions**:
- README sections inserted between "How It Works" and "Next Steps": Phase 0, Improvement Methodology, Variant Progression.
- "Next Steps" reframed to lead with the improvement cycle rather than infrastructure tasks.
- Tables kept compact with one example per row; full flywheel doc linked for depth.
- CLAUDE.md distinguishes build mode (infrastructure) from optimize mode (flywheel cycle).
- Build/optimize mode distinction placed before Dependencies — conceptual bridge between customization points and implementation.

**Vocabulary established**: cycle (RUN/MEASURE/DIAGNOSE/INTERVENE/VERIFY), 7 loss dimensions, 5 levers, 5 loop types, "empirically motivated," "the critical distinction."

## Stage 2: Configuration and Schema

**What was done**: Added `iteration` field to experiment-config.yaml, `IterationMetadata` nested record to VariantSpec.java, and YAML parsing in ExperimentApp.loadConfig().

**Key decisions**:
- `IterationMetadata` is a nested record in VariantSpec (not flat fields) — maps directly to the YAML `iteration:` block structure.
- `finding` is `@Nullable` (null for baseline), `hypothesis` is required.
- Parsing follows existing pattern: `(Map<String, Object>) rv.get("iteration")` then cast nested strings.
- When `iteration` absent from YAML, IterationMetadata is null — no enforcement at parse time.

**Pre-existing compile issue**: `ExperimentRunner` was renamed to `AgentExperiment` in experiment-core, and `Jury` moved packages. Template's SNAPSHOT dependency is stale. VariantSpec and the parsing code compile correctly in isolation.
