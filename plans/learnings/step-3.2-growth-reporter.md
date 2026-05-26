# Step 3.2: GrowthStoryReporter Enhancements

## Changes
1. **`appendIterationMotivation(VariantSpec)`** — new method that adds a "Motivation" subsection with finding and hypothesis when IterationMetadata is present. Safe no-op when metadata is null.
2. **Regression flagging in `appendComparison()`** — tracks whether any ScoreComparison has regressions > 0 and appends a WARNING block advising review before proceeding.
3. **ExperimentApp.runAllVariants()** — calls `appendIterationMotivation(variant)` before `appendComparison`/`appendBaseline` so the motivation appears before the score data.

## Verification
GrowthStoryReporter.java and VariantSpec.java compile cleanly together.
