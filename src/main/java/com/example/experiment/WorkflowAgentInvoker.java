package com.example.experiment;

import java.nio.file.Path;
import java.util.List;

import io.github.markpollack.agents.claude.ClaudeAgentModel;
import io.github.markpollack.agents.client.AgentClientResponse;
import io.github.markpollack.experiment.agent.InvocationContext;
import io.github.markpollack.journal.Journal;
import io.github.markpollack.journal.Run;
import io.github.markpollack.journal.storage.JsonFileStorage;
import io.github.markpollack.workflow.core.AgentContext;
import io.github.markpollack.workflow.flows.steps.AgentClient;
import io.github.markpollack.workflow.flows.steps.AgentClientStep;
import io.github.markpollack.workflow.flows.workflow.LocalStepRunner;
import io.github.markpollack.workflow.flows.workflow.Workflow;
import io.github.markpollack.workflow.flows.workflow.WorkflowExecutor;
import io.github.markpollack.workflow.journal.WorkflowJournal;
import org.jspecify.annotations.Nullable;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * AgentInvoker that uses agent-workflow's {@link Workflow} to orchestrate
 * a single {@link AgentClientStep} backed by {@link ClaudeAgentModel}.
 * <p>
 * Produces JSONL trace files per step and wires trace paths through the
 * workflow journal. This is the recommended invoker for experiments that
 * need tool-call traces (Markov analysis, cost attribution, debugging).
 */
public class WorkflowAgentInvoker extends AbstractTemplateAgentInvoker {

	private static final Logger logger = LoggerFactory.getLogger(WorkflowAgentInvoker.class);

	private static final Path TRACE_DIR = Path.of("experiments", "traces");

	private static final Path JOURNAL_DIR = Path.of("experiments", "traces", ".agent-journal");

	static {
		Journal.configure(new JsonFileStorage(JOURNAL_DIR));
		WorkflowJournal.registerEventType();
	}

	public WorkflowAgentInvoker() {
		super();
	}

	public WorkflowAgentInvoker(@Nullable Path knowledgeSourceDir, @Nullable List<String> knowledgeFiles) {
		super(knowledgeSourceDir, knowledgeFiles);
	}

	@Override
	protected AgentResult invokeAgent(InvocationContext context) {
		String experimentId = context.metadata().getOrDefault("experimentId", "experiment-run");
		logger.info("WorkflowAgentInvoker: executing single-step workflow for workspace: {}",
				context.workspacePath());

		try (ClaudeAgentModel model = ClaudeAgentModel.builder()
				.workingDirectory(context.workspacePath())
				.traceDir(TRACE_DIR)
				.build()) {

			var coreClient = io.github.markpollack.agents.client.AgentClient.create(model);

			AgentClient workflowClient = new AgentClient() {
				@Override
				public String execute(String prompt, AgentContext ctx) {
					return executeForResult(prompt, ctx).text();
				}

				@Override
				public ExecutionResult executeForResult(String prompt, AgentContext ctx) {
					AgentClientResponse response = coreClient.run(prompt);
					String tracePath = (String) response.getMetadata().get("tracePath");
					return new ExecutionResult(response.getResult(), tracePath);
				}
			};

			AgentClientStep agentStep = AgentClientStep.of(workflowClient, "{input}");

			try (Run run = Journal.run(experimentId).start()) {
				WorkflowExecutor executor = new WorkflowExecutor(new LocalStepRunner(),
						WorkflowJournal.forRun(run));

				String result = Workflow.<String, String>define("experiment-run")
					.withExecutor(executor)
					.step(agentStep)
					.run(context.prompt());

				logger.info("Workflow completed, response length: {} chars", result.length());
			}
		}

		return new AgentResult(List.of(), null);
	}

}
