package com.example.experiment;

import java.io.IOException;
import java.io.UncheckedIOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

import ai.tuvium.experiment.comparison.ComparisonResult;
import ai.tuvium.experiment.comparison.ExperimentSummary;
import ai.tuvium.experiment.comparison.ScoreComparison;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Reads experiment results and comparison data to produce a markdown comparison report.
 * The report shows how agent performance changes across prompt versions, providing
 * evidence for the "knowledge > prompt > model" thesis.
 *
 * <p>Output: {@code analysis/comparison-report.md}</p>
 */
public class GrowthStoryReporter {

	private static final Logger logger = LoggerFactory.getLogger(GrowthStoryReporter.class);

	private final Path analysisDir;

	private final List<String> sections = new ArrayList<>();

	public GrowthStoryReporter(Path analysisDir) {
		this.analysisDir = analysisDir;
	}

	/**
	 * Append the baseline variant summary (first variant, no comparison).
	 */
	public void appendBaseline(String variantName, ExperimentSummary summary) {
		StringBuilder sb = new StringBuilder();
		sb.append("### Prompt Version: ").append(variantName).append(" (Baseline)\n\n");
		sb.append("| Metric | Value |\n");
		sb.append("|--------|-------|\n");
		sb.append(String.format("| Pass Rate | %.1f%% |\n", summary.passRate() * 100));
		sb.append(String.format("| Total Cost | $%.4f |\n", summary.totalCostUsd()));
		sb.append(String.format("| Total Tokens | %,d |\n", summary.totalTokens()));
		sb.append(String.format("| Duration | %ds |\n", summary.totalDurationMs() / 1000));
		sb.append("\n");

		if (!summary.scoreAggregates().isEmpty()) {
			sb.append("**Scores:**\n\n");
			sb.append("| Judge | Mean Score |\n");
			sb.append("|-------|------------|\n");
			for (var entry : summary.scoreAggregates().entrySet()) {
				sb.append(String.format("| %s | %.3f |\n", entry.getKey(), entry.getValue()));
			}
			sb.append("\n");
		}

		sections.add(sb.toString());
	}

	/**
	 * Append a comparison between the current variant and its predecessor.
	 */
	public void appendComparison(String variantName, ComparisonResult comparison) {
		StringBuilder sb = new StringBuilder();
		sb.append("### Prompt Version: ").append(variantName).append(" (vs previous)\n\n");

		Map<String, ScoreComparison> scores = comparison.scoreComparisons();
		if (!scores.isEmpty()) {
			sb.append("| Judge | Current | Baseline | Delta | Improved | Regressed |\n");
			sb.append("|-------|---------|----------|-------|----------|----------|\n");
			for (var entry : scores.entrySet()) {
				ScoreComparison sc = entry.getValue();
				String deltaStr = sc.delta() >= 0 ? "+" + String.format("%.3f", sc.delta())
						: String.format("%.3f", sc.delta());
				sb.append(String.format("| %s | %.3f | %.3f | %s | %d | %d |\n", entry.getKey(), sc.currentMean(),
						sc.baselineMean(), deltaStr, sc.improvements(), sc.regressions()));
			}
			sb.append("\n");
		}

		ExperimentSummary summary = comparison.summary();
		sb.append(String.format("Pass rate: %.1f%% | Cost: $%.4f | Tokens: %,d\n\n", summary.passRate() * 100,
				summary.totalCostUsd(), summary.totalTokens()));

		sections.add(sb.toString());
	}

	/**
	 * Write the complete growth story to analysis/growth-story.md.
	 */
	public void generateReport() {
		try {
			Files.createDirectories(analysisDir);

			StringBuilder story = new StringBuilder();
			story.append("# Comparison Report\n\n");
			story.append("> Generated: ").append(Instant.now()).append("\n\n");
			story.append("## Prompt Version Progression\n\n");

			for (String section : sections) {
				story.append(section);
			}

			story.append("## Analysis\n\n");
			story.append("_TODO: Add analysis of what drove improvements across prompt versions._\n");

			Path outputPath = analysisDir.resolve("comparison-report.md");
			Files.writeString(outputPath, story.toString());
			logger.info("Comparison report written to {}", outputPath);
		}
		catch (IOException ex) {
			throw new UncheckedIOException("Failed to write growth story", ex);
		}
	}

}
