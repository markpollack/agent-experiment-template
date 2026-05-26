# Step 2.0: Stage 2 Entry

## VariantSpec structure

Record with 7 fields: name, promptFile, actPromptFile, knowledgeDir, knowledgeFiles, orchestration, judgeOverrides. Two convenience constructors (4-arg and 5-arg). Two boolean helpers (isTwoPhase, isWorkflow).

Adding `iteration` field as 8th parameter. Existing convenience constructors pass null.

## ExperimentApp.loadConfig() parsing

Line 435-466. Uses raw SnakeYAML `Map<String, Object>`. Loop at line 451 iterates `rawVariants`. Extraction pattern: `(Type) rv.get("key")`. VariantSpec constructed at line 460 with all 7 args.

To add iteration parsing: extract `(Map<String, Object>) rv.get("iteration")`, pull finding/hypothesis strings, construct IterationMetadata, pass to VariantSpec.

## Design confirmed

- `iteration` is optional — null when absent
- `hypothesis` is required within IterationMetadata
- `finding` is nullable (null for baseline)
- No backward compat needed
