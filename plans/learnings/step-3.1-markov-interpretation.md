# Step 3.1: Markov Interpretation Output

Added `write_interpretation()` function to `make_markov_analysis.py` that writes `analysis/markov-interpretation.md`.

## What it generates
- **Loop Amplification Summary** table: per-variant, per-state amplification with classification (HIGH/moderate), recommended lever, and suggestion — all mapped from flywheel vocabulary.
- **Suggested Next Variant** section: identifies the highest-amplification state in the latest variant and templates a hypothesis for the next intervention.
- **Low Amplification** section: lists variants with no friction/failure loops.

## Thresholds
- HIGH: amplification >= 2.0 (friction or failure loop)
- moderate: amplification >= 1.5 (worth watching)
- Below 1.5: not reported

## Integration
- Captures `pipeline.run()` return value (was discarded before)
- Calls `write_interpretation(results)` after pipeline completes
- Existing figure generation unchanged
