package com.example.experiment;

import java.io.IOException;
import java.io.InputStream;
import java.io.UncheckedIOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Duration;
import java.time.Instant;
import java.time.ZoneOffset;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Optional;

import ai.tuvium.experiment.agent.AgentInvoker;
import ai.tuvium.experiment.comparison.ComparisonEngine;
import ai.tuvium.experiment.comparison.ComparisonResult;
import ai.tuvium.experiment.comparison.DefaultComparisonEngine;
import ai.tuvium.experiment.comparison.DiffStatus;
import ai.tuvium.experiment.comparison.ItemDiff;
import ai.tuvium.experiment.dataset.DatasetManager;
import ai.tuvium.experiment.dataset.FileSystemDatasetManager;
import ai.tuvium.experiment.result.ExperimentResult;
import ai.tuvium.experiment.runner.ExperimentConfig;
import ai.tuvium.experiment.runner.ExperimentRunner;
import ai.tuvium.experiment.store.ActiveSession;
import ai.tuvium.experiment.store.FileSystemResultStore;
import ai.tuvium.experiment.store.FileSystemSessionStore;
import ai.tuvium.experiment.store.ResultStore;
import ai.tuvium.experiment.store.SessionStore;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springaicommunity.judge.exec.BuildSuccessJudge;
import org.springaicommunity.judge.jury.Jury;
import org.springaicommunity.judge.jury.TierPolicy;
import org.yaml.snakeyaml.Yaml;

/**
 * Pre-wired experiment application. Reads variant configurations, iterates through
 * each variant, runs the experiment loop, and produces a growth story comparing results
 * across variants.
 *
 * <p>Domain-specific projects customize this by providing:
 * <ul>
 *   <li>A concrete {@link AgentInvoker} implementation</li>
 *   <li>Custom judges (if any)</li>
 *   <li>Knowledge files and prompts per variant</li>
 * </ul>
 */
public class ExperimentApp {

	private static final Logger logger = LoggerFactory.getLogger(ExperimentApp.class);

	private static final DateTimeFormatter SESSION_NAME_FORMAT = DateTimeFormatter.ofPattern("yyyyMMdd-HHmmss")
		.withZone(ZoneOffset.UTC);

	private final ExperimentVariantConfig variantConfig;

	private final JuryFactory juryFactory;

	private final ResultStore resultStore;

	private final SessionStore sessionStore;

	private final ComparisonEngine comparisonEngine;

	private final GrowthStoryReporter reporter;

	private final Path projectRoot;

	public ExperimentApp(ExperimentVariantConfig variantConfig, JuryFactory juryFactory,
			ResultStore resultStore, SessionStore sessionStore, Path projectRoot) {
		this.variantConfig = variantConfig;
		this.juryFactory = juryFactory;
		this.resultStore = resultStore;
		this.sessionStore = sessionStore;
		this.comparisonEngine = new DefaultComparisonEngine(resultStore);
		this.reporter = new GrowthStoryReporter(projectRoot.resolve("analysis"));
		this.projectRoot = projectRoot;
	}

	/**
	 * Run a single variant experiment within a session.
	 */
	public ExperimentResult runVariant(VariantSpec variant, String sessionName) {
		logger.info("Running variant: {} (session: {})", variant.name(), sessionName);

		Jury jury = juryFactory.build(variant);
		AgentInvoker invoker = createInvoker(variant);

		ExperimentConfig config = ExperimentConfig.builder()
			.experimentName(variantConfig.experimentName())
			.datasetDir(projectRoot.resolve("dataset"))
			.promptTemplate(loadPrompt(variant))
			.model(variantConfig.defaultModel())
			.perItemTimeout(Duration.ofMinutes(variantConfig.timeoutMinutes()))
			.knowledgeBaseDir(variant.knowledgeDir() != null ? projectRoot.resolve(variant.knowledgeDir()) : null)
			.preserveWorkspaces(true)
			.outputDir(projectRoot.resolve("results"))
			.build();

		DatasetManager datasetManager = variantConfig.itemSlugFilter() != null
				? new SlugFilteringDatasetManager(variantConfig.datasetManager(), variantConfig.itemSlugFilter())
				: variantConfig.datasetManager();

		ExperimentRunner runner = new ExperimentRunner(
				datasetManager, jury, resultStore, sessionStore, config);

		ActiveSession activeSession = new ActiveSession(
				sessionName, variantConfig.experimentName(), variant.name());

		ExperimentResult result = runner.run(invoker, activeSession);

		logger.info("Variant '{}' complete: passRate={}, cost=${}",
				variant.name(),
				String.format("%.1f%%", result.passRate() * 100),
				String.format("%.4f", result.totalCostUsd()));

		return result;
	}

	/**
	 * Run all variants in sequence within a single session.
	 */
	public void runAllVariants() {
		List<VariantSpec> variants = variantConfig.variants();
		String sessionName = SESSION_NAME_FORMAT.format(Instant.now());

		logger.info("Running {} variants for experiment '{}' (session: {})",
				variants.size(), variantConfig.experimentName(), sessionName);

		sessionStore.createSession(sessionName, variantConfig.experimentName(), Map.of());

		ExperimentResult previousResult = null;

		for (VariantSpec variant : variants) {
			ExperimentResult result = runVariant(variant, sessionName);

			if (previousResult != null) {
				ComparisonResult comparison = comparisonEngine.compare(result, previousResult);
				reporter.appendComparison(variant.name(), comparison);
			}
			else {
				reporter.appendBaseline(variant.name(), comparisonEngine.summarize(result));
			}

			previousResult = result;
		}

		reporter.generateReport();
		logger.info("Comparison report written to analysis/comparison-report.md");
	}

	/**
	 * Print a human-readable results summary from the most recent run.
	 */
	public void printSummary() {
		Optional<ExperimentResult> latest = resultStore.mostRecent(variantConfig.experimentName());
		if (latest.isEmpty()) {
			System.out.println("No results found for experiment '" + variantConfig.experimentName() + "'.");
			System.out.println("Run a variant first: --variant control");
			return;
		}

		ExperimentResult result = latest.get();
		DateTimeFormatter fmt = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss 'UTC'").withZone(ZoneOffset.UTC);

		System.out.println();
		System.out.printf("=== Results: %s ===%n", variantConfig.experimentName());
		System.out.printf("Run: %s%n%n", fmt.format(result.timestamp()));

		// Find max slug length for alignment
		int maxSlug = result.items().stream().mapToInt(item -> item.itemSlug().length()).max().orElse(20);
		maxSlug = Math.max(maxSlug, 4); // "Repo" header

		System.out.printf("  %-" + maxSlug + "s   Pass?   Cost        Time%n", "Repo");
		for (var item : result.items()) {
			String passStr = item.passed() ? "\u2713" : "\u2717";
			String costStr = String.format("$%.4f", item.costUsd());
			String timeStr = formatDuration(item.durationMs());
			System.out.printf("  %-" + maxSlug + "s   %s       %-11s %s%n", item.itemSlug(), passStr, costStr,
					timeStr);
		}

		int passed = (int) result.items().stream().filter(item -> item.passed()).count();
		int total = result.items().size();
		System.out.println();
		System.out.printf("  Pass rate: %.1f%% (%d/%d)%n", result.passRate() * 100, passed, total);
		System.out.printf("  Total cost: $%.4f%n", result.totalCostUsd());
		System.out.printf("  Total time: %s%n", formatDuration(result.totalDurationMs()));
		System.out.println();
	}

	/**
	 * Print a side-by-side comparison of the two most recent runs.
	 */
	public void printComparison() {
		List<ExperimentResult> results = resultStore.listByName(variantConfig.experimentName());
		if (results.size() < 2) {
			System.out.println("Need at least 2 runs to compare.");
			if (results.isEmpty()) {
				System.out.println("Run a variant first: --variant control");
			}
			else {
				System.out.println("Run another variant: --variant variant-a");
			}
			return;
		}

		ExperimentResult baseline = results.get(results.size() - 2);
		ExperimentResult current = results.get(results.size() - 1);

		ComparisonResult comparison = comparisonEngine.compare(current, baseline);

		// Determine labels from metadata or index
		String baseLabel = baseline.metadata().getOrDefault("variant", "run-" + (results.size() - 1));
		String curLabel = current.metadata().getOrDefault("variant", "run-" + results.size());

		System.out.println();
		System.out.printf("=== Comparison: %s \u2192 %s ===%n%n", baseLabel, curLabel);

		// Find max slug length
		int maxSlug = comparison.itemDiffs()
			.stream()
			.mapToInt(diff -> diff.itemId().length())
			.max()
			.orElse(20);
		maxSlug = Math.max(maxSlug, 4);

		System.out.printf("  %-" + maxSlug + "s   %-10s %-10s Change%n", "Repo", baseLabel, curLabel);
		for (ItemDiff diff : comparison.itemDiffs()) {
			String basePass = getPassStr(baseline, diff.itemId());
			String curPass = getPassStr(current, diff.itemId());
			String change = switch (diff.status()) {
				case IMPROVED -> "Fixed!";
				case REGRESSED -> "Broke!";
				case NEW -> "New";
				case REMOVED -> "Removed";
				default -> "\u2014";
			};
			System.out.printf("  %-" + maxSlug + "s   %-10s %-10s %s%n", diff.itemId(), basePass, curPass, change);
		}

		double basePassRate = baseline.passRate() * 100;
		double curPassRate = current.passRate() * 100;
		double passRateDelta = curPassRate - basePassRate;
		double costDelta = current.totalCostUsd() - baseline.totalCostUsd();

		System.out.println();
		System.out.printf("  Pass rate: %.1f%% \u2192 %.1f%% (%+.1f%%)%n", basePassRate, curPassRate, passRateDelta);
		System.out.printf("  Cost: $%.2f \u2192 $%.2f (%+$%.2f)%n", baseline.totalCostUsd(),
				current.totalCostUsd(), costDelta);
		System.out.println();
	}

	private String getPassStr(ExperimentResult result, String itemId) {
		return result.items()
			.stream()
			.filter(item -> item.itemId().equals(itemId))
			.findFirst()
			.map(item -> item.passed() ? "\u2713" : "\u2717")
			.orElse("-");
	}

	private static String formatDuration(long ms) {
		if (ms < 1000) {
			return ms + "ms";
		}
		long seconds = ms / 1000;
		if (seconds < 60) {
			return seconds + "s";
		}
		long minutes = seconds / 60;
		long remainSeconds = seconds % 60;
		return minutes + "m " + remainSeconds + "s";
	}

	/**
	 * Create a per-variant invoker. Override this in domain-specific subclasses
	 * to dispatch single-phase vs two-phase invokers based on variant config.
	 */
	AgentInvoker createInvoker(VariantSpec variant) {
		if (variant.isTwoPhase()) {
			String actPrompt = loadPromptFile(variant.actPromptFile());
			return new TwoPhaseTemplateAgentInvoker(actPrompt);
		}
		return new TemplateAgentInvoker();
	}

	private String loadPrompt(VariantSpec variant) {
		return loadPromptFile(variant.promptFile());
	}

	private String loadPromptFile(String promptFileName) {
		Path promptPath = projectRoot.resolve("prompts").resolve(promptFileName);
		try {
			return Files.readString(promptPath);
		}
		catch (IOException ex) {
			throw new UncheckedIOException("Failed to load prompt: " + promptPath, ex);
		}
	}

	/**
	 * Load experiment configuration from a YAML file.
	 * @param configPath path to experiment-config.yaml
	 * @return parsed configuration with a {@link FileSystemDatasetManager}
	 */
	@SuppressWarnings("unchecked")
	static ExperimentVariantConfig loadConfig(Path configPath) {
		Yaml yaml = new Yaml();
		Map<String, Object> raw;
		try (InputStream in = Files.newInputStream(configPath)) {
			raw = yaml.load(in);
		}
		catch (IOException ex) {
			throw new UncheckedIOException("Failed to load config: " + configPath, ex);
		}

		String experimentName = (String) raw.get("experimentName");
		String defaultModel = (String) raw.get("defaultModel");
		int timeoutMinutes = (int) raw.get("timeoutMinutes");

		List<Map<String, Object>> rawVariants = (List<Map<String, Object>>) raw.get("variants");
		List<VariantSpec> variants = new ArrayList<>();
		for (Map<String, Object> rv : rawVariants) {
			String name = (String) rv.get("name");
			String promptFile = (String) rv.get("promptFile");
			String actPromptFile = (String) rv.get("actPromptFile");
			String knowledgeDir = (String) rv.get("knowledgeDir");
			List<String> knowledgeFiles = rv.get("knowledgeFiles") != null
					? (List<String>) rv.get("knowledgeFiles")
					: List.of();
			variants.add(new VariantSpec(name, promptFile, actPromptFile, knowledgeDir, knowledgeFiles));
		}

		return new ExperimentVariantConfig(
				experimentName, defaultModel, timeoutMinutes,
				List.copyOf(variants), new FileSystemDatasetManager());
	}

	/**
	 * Build the standard jury factory with tier-0 BuildSuccessJudge pre-wired.
	 * Domain projects add custom judges to higher tiers.
	 */
	static JuryFactory buildJuryFactory(Path projectRoot) {
		return JuryFactory.builder()
			.addJudge(0, BuildSuccessJudge.maven("clean", "test"))
			.tierPolicy(0, TierPolicy.REJECT_ON_ANY_FAIL)
			// TODO: Add domain-specific judges at tiers 1-3
			.build();
	}

	/**
	 * Main entry point. Usage:
	 * <pre>
	 *   ./mvnw compile exec:java -Dexec.args="--variant control"
	 *   ./mvnw compile exec:java -Dexec.args="--variant control --item example-project"
	 *   ./mvnw compile exec:java -Dexec.args="--run-all-variants"
	 *   ./mvnw compile exec:java -Dexec.args="--summary"
	 *   ./mvnw compile exec:java -Dexec.args="--compare"
	 * </pre>
	 */
	public static void main(String[] args) {
		Path projectRoot = Path.of(System.getProperty("user.dir"));

		// Parse CLI arguments
		String targetVariant = null;
		String targetItem = null;
		boolean runAll = false;
		boolean showSummary = false;
		boolean showCompare = false;

		for (int i = 0; i < args.length; i++) {
			switch (args[i]) {
				case "--variant" -> {
					if (i + 1 >= args.length) {
						logger.error("--variant requires a variant name");
						System.exit(1);
					}
					targetVariant = args[++i];
				}
				case "--item" -> {
					if (i + 1 >= args.length) {
						logger.error("--item requires an item slug");
						System.exit(1);
					}
					targetItem = args[++i];
				}
				case "--run-all-variants" -> runAll = true;
				case "--summary" -> showSummary = true;
				case "--compare" -> showCompare = true;
				case "--project-root" -> {
					if (i + 1 >= args.length) {
						logger.error("--project-root requires a path");
						System.exit(1);
					}
					projectRoot = Path.of(args[++i]);
				}
				default -> {
					logger.error("Unknown argument: {}", args[i]);
					System.exit(1);
				}
			}
		}

		if (targetVariant == null && !runAll && !showSummary && !showCompare) {
			logger.error("Usage: --variant <name> | --run-all-variants | --summary | --compare [--item <slug>] [--project-root <path>]");
			System.exit(1);
		}

		// Load config
		ExperimentVariantConfig variantConfig = loadConfig(projectRoot.resolve("experiment-config.yaml"));

		// Apply item filter if specified
		if (targetItem != null) {
			variantConfig = variantConfig.withItemFilter(targetItem);
			logger.info("Filtering to single item: {}", targetItem);
		}

		final ExperimentVariantConfig config = variantConfig;
		logger.info("Loaded experiment '{}' with {} variants (model={}, timeout={}min)",
				config.experimentName(), config.variants().size(),
				config.defaultModel(), config.timeoutMinutes());

		// Wire components
		Path resultsDir = projectRoot.resolve("results");
		ResultStore resultStore = new FileSystemResultStore(resultsDir);
		SessionStore sessionStore = new FileSystemSessionStore(resultsDir);
		JuryFactory juryFactory = buildJuryFactory(projectRoot);

		ExperimentApp app = new ExperimentApp(config, juryFactory, resultStore, sessionStore, projectRoot);

		// Dispatch
		if (showSummary) {
			app.printSummary();
		}
		else if (showCompare) {
			app.printComparison();
		}
		else if (runAll) {
			app.runAllVariants();
		}
		else {
			String variantName = targetVariant;
			VariantSpec variant = config.variants().stream()
				.filter(v -> v.name().equals(variantName))
				.findFirst()
				.orElseThrow(() -> new IllegalArgumentException(
						"Unknown variant: " + variantName + ". Available: "
								+ config.variants().stream().map(VariantSpec::name).toList()));

			String sessionName = SESSION_NAME_FORMAT.format(Instant.now());
			sessionStore.createSession(sessionName, config.experimentName(), Map.of());
			app.runVariant(variant, sessionName);
		}
	}

}
