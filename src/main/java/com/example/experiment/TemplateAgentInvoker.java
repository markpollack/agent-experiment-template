package com.example.experiment;

import java.nio.file.Path;
import java.util.List;

import ai.tuvium.experiment.agent.InvocationContext;
import org.jspecify.annotations.Nullable;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Single-phase AgentInvoker implementation. Replace this with your domain-specific
 * invoker that wraps AgentClient and implements the actual agent interaction.
 *
 * <p>This placeholder logs the invocation and returns a successful no-op result,
 * allowing the experiment loop to be tested before the real agent is wired in.</p>
 *
 * <p><strong>To customize:</strong></p>
 * <ol>
 *   <li>Rename this class to {@code {Domain}AgentInvoker}</li>
 *   <li>Inject an {@link org.springaicommunity.agents.client.AgentClient}</li>
 *   <li>Override {@link #preInvoke} for domain-specific setup</li>
 *   <li>Implement {@link #invokeAgent} with real agent interaction</li>
 *   <li>Override {@link #postInvoke} for domain-specific measurement</li>
 * </ol>
 */
public class TemplateAgentInvoker extends AbstractTemplateAgentInvoker {

	private static final Logger logger = LoggerFactory.getLogger(TemplateAgentInvoker.class);

	public TemplateAgentInvoker() {
		super();
	}

	public TemplateAgentInvoker(@Nullable Path knowledgeSourceDir, @Nullable List<String> knowledgeFiles) {
		super(knowledgeSourceDir, knowledgeFiles);
	}

	@Override
	protected AgentResult invokeAgent(InvocationContext context) {
		logger.info("TemplateAgentInvoker invoked for workspace: {}", context.workspacePath());
		logger.info("Prompt length: {} chars", context.prompt().length());
		logger.info("Model: {}", context.model());
		logger.warn("This is a placeholder — replace with your domain-specific AgentInvoker");

		// Placeholder: return an empty result
		return new AgentResult(List.of(), null);
	}

}
