package com.example.experiment;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.Map;
import java.util.stream.Stream;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import io.github.markpollack.experiment.agent.AgentInvoker;
import io.github.markpollack.experiment.dataset.FileSystemDatasetManager;
import io.github.markpollack.experiment.store.FileSystemResultStore;
import io.github.markpollack.experiment.store.FileSystemSessionStore;
import io.github.markpollack.experiment.store.ResultStore;
import io.github.markpollack.experiment.store.SessionStore;
import io.github.markpollack.experiment.workflow.AbstractTemplateAgentInvoker;
import io.github.markpollack.journal.Journal;
import io.github.markpollack.journal.claude.PhaseCapture;
import io.github.markpollack.journal.claude.ToolUseRecord;
import io.github.markpollack.journal.claude.TurnUsage;
import io.github.markpollack.judge.Judge;
import io.github.markpollack.judge.JudgeMetadata;
import io.github.markpollack.judge.JudgeType;
import io.github.markpollack.judge.JudgeWithMetadata;
import io.github.markpollack.judge.context.JudgmentContext;
import io.github.markpollack.judge.jury.TierPolicy;
import io.github.markpollack.judge.result.Judgment;
import io.github.markpollack.judge.result.JudgmentStatus;
import io.github.markpollack.judge.score.BooleanScore;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * On-by-default journal-capture guard — the agent-experiment-template slice of the
 * first-class journal-capture feature (DESIGN §6 guarantee #3: "on-by-default in the
 * template — every future experiment inherits it").
 *
 * <p>
 * This drives the template's real wiring — {@link ExperimentApp#runVariant} builds the
 * {@link io.github.markpollack.experiment.runner.ExperimentConfig} (notably its
 * {@code outputDir}), and experiment-core owns the run-journal lifecycle — with a
 * synthetic-phase {@link AgentInvoker}. The invoker returns only a {@link PhaseCapture}
 * (two tool calls + per-turn usage) and contains <strong>zero journal code</strong>, yet a
 * canonical journal appears on disk: an {@code analysis.jsonl} with derived
 * {@code StepCostEvent}s keyed by tool_use id, behind an A5 schema header. If a future
 * change drops {@code outputDir} (or otherwise breaks the default), this test fails — the
 * exact regression that left v3/v4 with no per-tool cost.
 */
class JournalCaptureSmokeTest {

	private static final ObjectMapper MAPPER = new ObjectMapper();

	@AfterEach
	void tearDown() {
		// agent-journal's Journal context (storage + experiment registry) is process-global.
		Journal.reset();
	}

	@Test
	void freshExperimentWritesCanonicalJournalWithNoAuthorJournalCode(@TempDir Path projectRoot) throws Exception {
		bootstrapProject(projectRoot);

		VariantSpec control = new VariantSpec("control", "v0-naive.txt", null, List.of());
		ExperimentVariantConfig variantConfig = new ExperimentVariantConfig("journal-smoke", "claude-sonnet-4-6", 15,
				List.of(control), new FileSystemDatasetManager());

		Path resultsDir = projectRoot.resolve("results");
		ResultStore resultStore = new FileSystemResultStore(resultsDir);
		SessionStore sessionStore = new FileSystemSessionStore(resultsDir);
		JuryFactory passingJury = JuryFactory.builder()
			.addJudge(0, new PassingJudge())
			.tierPolicy(0, TierPolicy.FINAL_TIER)
			.build();

		// The template's own ExperimentApp, with the only customization an author ever
		// makes: the AgentInvoker. It returns a PhaseCapture and nothing else.
		ExperimentApp app = new ExperimentApp(variantConfig, passingJury, resultStore, sessionStore, null,
				projectRoot) {
			@Override
			AgentInvoker createInvoker(VariantSpec variant) {
				return new SyntheticPhaseInvoker();
			}
		};

		String sessionName = "smoke-session";
		sessionStore.createSession(sessionName, variantConfig.experimentName(), Map.of());
		app.runVariant(control, sessionName);

		// A canonical analysis.jsonl exists with the A5 header followed by step_cost events.
		List<Path> analysisFiles = findFiles(resultsDir, "analysis.jsonl");
		assertThat(analysisFiles).as("canonical analysis.jsonl written under results/").isNotEmpty();

		List<String> lines = Files.readAllLines(analysisFiles.get(0));
		assertThat(lines).isNotEmpty();

		JsonNode header = MAPPER.readTree(lines.get(0));
		assertThat(header.get("@type").asText()).isEqualTo("header");
		assertThat(header.get("schemaVersion").asInt()).isEqualTo(1);
		assertThat(header.get("stream").asText()).isEqualTo("analysis");

		List<JsonNode> stepCosts = lines.stream()
			.filter(l -> !l.isBlank())
			.map(JournalCaptureSmokeTest::readTree)
			.filter(n -> "step_cost".equals(n.path("@type").asText()))
			.toList();
		assertThat(stepCosts).as("derived per-tool StepCostEvents").hasSize(2);
		assertThat(stepCosts).map(n -> n.get("stepId").asText()).containsExactlyInAnyOrder("toolu_01", "toolu_02");
		assertThat(stepCosts).allSatisfy(node -> {
			// Cost is an allocation, not a measurement — the precise split is labelled so.
			assertThat(node.get("attributionMethod").asText()).isEqualTo("OUTPUT_TOKEN_PROPORTIONAL");
			assertThat(node.has("attributedCostUsd")).isTrue();
		});

		// The immutable execution stream is written alongside, also behind an A5 header.
		List<Path> eventsFiles = findFiles(resultsDir, "events.jsonl");
		assertThat(eventsFiles).isNotEmpty();
		assertThat(Files.readString(eventsFiles.get(0))).contains("toolu_01").contains("toolu_02");
	}

	/**
	 * Lays down the minimal files a bootstrapped experiment has: one prompt and a
	 * filesystem dataset with a single locally-resolvable item.
	 */
	private static void bootstrapProject(Path projectRoot) throws Exception {
		Path prompts = Files.createDirectories(projectRoot.resolve("prompts"));
		Files.writeString(prompts.resolve("v0-naive.txt"), "{{task}}");

		Path dataset = Files.createDirectories(projectRoot.resolve("dataset"));
		Files.writeString(dataset.resolve("dataset.json"), """
				{
				  "schemaVersion": 1,
				  "name": "journal-smoke-dataset",
				  "version": "1.0.0",
				  "items": [ { "id": "smoke-001", "slug": "smoke", "path": "smoke" } ]
				}
				""");
		Path itemDir = Files.createDirectories(dataset.resolve("smoke"));
		Files.writeString(itemDir.resolve("item.json"), """
				{ "developerTask": "do the smoke task" }
				""");
		Path before = Files.createDirectories(itemDir.resolve("before"));
		Files.writeString(before.resolve("README.md"), "smoke workspace seed\n");
	}

	/** A phase with two parallel tool calls + per-turn usage → OUTPUT_TOKEN_PROPORTIONAL. */
	private static PhaseCapture twoToolPhase() {
		ToolUseRecord read = new ToolUseRecord("toolu_01", "Read", Map.of("file_path", "Foo.java"));
		ToolUseRecord bash = new ToolUseRecord("toolu_02", "Bash", Map.of("command", "ls"));
		TurnUsage turn = new TurnUsage("msg_1", "claude-sonnet-4-6", 1000, 200, 0, 0, List.of("toolu_01", "toolu_02"));
		return new PhaseCapture("explore", "do the task", 1000, 200, 0, 0, 0, 1500L, 1200L, 0.02, "session-abc", 1,
				false, "all done", List.of(), List.of(read, bash), "result text", List.of(), List.of(turn), List.of());
	}

	/**
	 * The only author-supplied piece: returns a PhaseCapture. No journal code — the
	 * framework journals it because the template wired an outputDir.
	 */
	private static final class SyntheticPhaseInvoker extends AbstractTemplateAgentInvoker {

		@Override
		protected AgentResult invokeAgent(io.github.markpollack.experiment.agent.InvocationContext context) {
			return new AgentResult(List.of(twoToolPhase()), "session-abc");
		}

	}

	private static final class PassingJudge implements Judge, JudgeWithMetadata {

		private final JudgeMetadata metadata = new JudgeMetadata("smoke_judge", "Always passes (smoke)",
				JudgeType.DETERMINISTIC);

		@Override
		public Judgment judge(JudgmentContext context) {
			return Judgment.builder()
				.score(new BooleanScore(true))
				.status(JudgmentStatus.PASS)
				.reasoning("smoke")
				.build();
		}

		@Override
		public JudgeMetadata metadata() {
			return metadata;
		}

	}

	private static JsonNode readTree(String line) {
		try {
			return MAPPER.readTree(line);
		}
		catch (Exception ex) {
			throw new RuntimeException(ex);
		}
	}

	private static List<Path> findFiles(Path root, String fileName) throws Exception {
		try (Stream<Path> walk = Files.walk(root)) {
			return walk.filter(Files::isRegularFile)
				.filter(p -> p.getFileName().toString().equals(fileName))
				.toList();
		}
	}

}
