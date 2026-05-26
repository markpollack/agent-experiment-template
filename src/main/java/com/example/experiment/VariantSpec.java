package com.example.experiment;

import java.util.List;

import org.jspecify.annotations.Nullable;

/**
 * Specification for a single experiment variant. Each variant represents a
 * different configuration of prompt, knowledge, and judges to evaluate.
 *
 * @param name variant identifier (e.g., "control", "variant-a")
 * @param promptFile filename in prompts/ directory (explore prompt for two-phase)
 * @param actPromptFile filename in prompts/ for act phase (null for single-phase)
 * @param knowledgeDir relative path to knowledge directory (null for no knowledge)
 * @param knowledgeFiles specific knowledge files to include
 * @param orchestration orchestration mode: null/"direct" for legacy, "workflow" for agent-workflow
 * @param judgeOverrides judge configuration overrides for this variant
 */
public record VariantSpec(
		String name,
		String promptFile,
		@Nullable String actPromptFile,
		String knowledgeDir,
		List<String> knowledgeFiles,
		@Nullable String orchestration,
		java.util.Map<String, String> judgeOverrides,
		@Nullable IterationMetadata iteration) {

	/**
	 * Iteration metadata linking a variant to the observation that motivated it.
	 * @param finding observation from the prior variant's analysis (null for baseline)
	 * @param hypothesis what this variant tests — the expected improvement
	 */
	public record IterationMetadata(@Nullable String finding, String hypothesis) {}

	public VariantSpec(String name, String promptFile, String knowledgeDir, List<String> knowledgeFiles) {
		this(name, promptFile, null, knowledgeDir, knowledgeFiles, null, null, null);
	}

	public VariantSpec(String name, String promptFile, @Nullable String actPromptFile,
			String knowledgeDir, List<String> knowledgeFiles) {
		this(name, promptFile, actPromptFile, knowledgeDir, knowledgeFiles, null, null, null);
	}

	/** Whether this variant uses a two-phase (explore + act) invocation pattern. */
	public boolean isTwoPhase() {
		return actPromptFile != null;
	}

	/** Whether this variant uses agent-workflow orchestration. */
	public boolean isWorkflow() {
		return "workflow".equals(orchestration);
	}

}
