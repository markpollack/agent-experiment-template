# Inbox: Wire the Iterative Flywheel into the Template

**From**: bud-eval session (2026-05-25)
**Companion to**: `~/projects/forge/plans/inbox/codify-iterative-flywheel.md`

## Context

The experiment template has the pieces (journal capture, Markov scripts, variant progression) but the flywheel loop isn't connected. See the forge inbox note for the full methodology writeup.

## Template changes needed

1. **README**: Add Phase 0 Discovery section describing the empirical state taxonomy step
2. **ResultStore**: Wire `PhaseCapture` from `AbstractTemplateAgentInvoker` into persistent storage
3. **Iteration tracking**: Record what changed between runs + delta measurement per criterion
4. **make_markov_analysis.py**: Add interpretation guidance in output (not just figures)
5. **experiment-config.yaml**: Add `iteration` field to variant specs linking each to its motivating finding

## Key principle: deterministic over exploratory

The flywheel consistently shows that converting exploratory LLM behavior into deterministic steps improves quality:

- Bud's cached templates (deterministic scaffolding) score 0.70-0.93
- Bud's expansion path (LLM exploration) scores 0.28-0.72 and is unreliable
- Raw Claude Code (pure exploration) scores 0.19-0.63

The experiment methodology should explicitly note: **when the Markov analysis reveals that the agent consistently discovers the same pattern through exploration, codify that pattern as a deterministic step (template, recipe, knowledge file).** The goal of each iteration is to shrink the agent's exploration space by converting discovered knowledge into structured execution.

This is the entropy thesis: every decision point the LLM doesn't have to make is a source of variance eliminated. The flywheel's purpose is to systematically find and eliminate these decision points.
