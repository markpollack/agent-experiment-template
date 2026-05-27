package com.example.experiment;

import java.nio.file.Path;
import java.util.List;

import io.github.markpollack.experiment.agent.InvocationContext;
import io.github.markpollack.journal.Journal;
import io.github.markpollack.journal.Run;
import io.github.markpollack.workflow.flows.steps.ClaudeStep;
import io.github.markpollack.workflow.flows.steps.PermissionMode;
import io.github.markpollack.workflow.flows.workflow.LocalStepRunner;
import io.github.markpollack.workflow.flows.workflow.Workflow;
import io.github.markpollack.workflow.flows.workflow.WorkflowExecutor;
import io.github.markpollack.workflow.journal.WorkflowJournal;
import org.jspecify.annotations.Nullable;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * AgentInvoker that uses agent-workflow's {@link Workflow} to orchestrate
 * a single {@link ClaudeStep}. This provides the foundation for evolving
 * toward multi-step workflows (gates, parallel branches, loops) without
 * changing the experiment framework contract.
 */
public class WorkflowAgentInvoker extends AbstractTemplateAgentInvoker {

	private static final Logger logger = LoggerFactory.getLogger(WorkflowAgentInvoker.class);

	static {
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

		try (Run run = Journal.run(experimentId).start()) {
			ClaudeStep claudeStep = ClaudeStep.of("{input}")
				.workingDirectory(context.workspacePath())
				.permissionMode(PermissionMode.BYPASS_PERMISSIONS);

			WorkflowExecutor executor = new WorkflowExecutor(new LocalStepRunner(),
					WorkflowJournal.forRun(run));

			String result = Workflow.<String, String>define("experiment-run")
				.withExecutor(executor)
				.step(claudeStep)
				.run(context.prompt());

			logger.info("Workflow completed, response length: {} chars", result.length());
		}

		return new AgentResult(List.of(), null);
	}

}
