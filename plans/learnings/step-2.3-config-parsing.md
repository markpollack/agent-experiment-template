# Step 2.3: Config Parsing for Iteration Field

Added iteration parsing to `ExperimentApp.loadConfig()`. Extracts `iteration` map from each variant's raw YAML, pulls `finding` and `hypothesis` strings, constructs `IterationMetadata`, passes to VariantSpec constructor.

Pattern matches existing optional field handling (e.g., `actPromptFile`, `orchestration`). When `iteration` is absent from YAML, IterationMetadata is null.
