# Step 2.K: Stage 2 Summary

Stage 2 added iteration metadata to the configuration and schema layer.

## Files changed
- `experiment-config.yaml` — `iteration` block on each variant (finding + hypothesis)
- `VariantSpec.java` — `IterationMetadata` nested record, `@Nullable iteration` field
- `ExperimentApp.java` — Parse `iteration` map from YAML, construct IterationMetadata

## Ready for Stage 3
Analysis and reporting enhancements: add interpretation output to make_markov_analysis.py, enhance GrowthStoryReporter with regression flagging and iteration motivation.
