# Step 2.2: VariantSpec IterationMetadata

Added `IterationMetadata` nested record and `@Nullable IterationMetadata iteration` field to VariantSpec. Existing convenience constructors pass null. VariantSpec.java compiles cleanly in isolation.

Note: `./mvnw compile` has pre-existing failures (ExperimentRunner renamed to AgentExperiment in experiment-core, Jury package moved). These are unrelated to the VariantSpec changes. Isolated javac compilation of VariantSpec.java succeeds.
