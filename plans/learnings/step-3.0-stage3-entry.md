# Step 3.0: Stage 3 Entry

## Markov analysis script
- `pipeline.run()` returns dict with `amplification` key
- Amplification: `dict[variant, dict[state, float]]` — per-state amplification factors
- Script already writes `analysis/markov-findings.md` — new interpretation file goes to `analysis/markov-interpretation.md`
- Pipeline already has `analysis_dir` parameter pointing to `PROJECT_ROOT / "analysis"`

## GrowthStoryReporter
- `appendComparison()` already shows per-judge improvements/regressions counts in a table
- `ScoreComparison` has: `currentMean()`, `baselineMean()`, `delta()`, `improvements()`, `regressions()`
- No explicit regression warning text yet — just numbers in the table
- Need to add: regression warning when `regressions() > 0`, iteration motivation section

## Plan
- Step 3.1: Add interpretation output to make_markov_analysis.py using `results['amplification']`
- Step 3.2: Enhance GrowthStoryReporter with regression flags and appendIterationMotivation
