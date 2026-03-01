package io.github.markpollack.experiment;

import ai.tuvium.experiment.agent.AgentInvocationException;
import ai.tuvium.experiment.agent.AgentInvoker;
import ai.tuvium.experiment.agent.InvocationContext;
import ai.tuvium.experiment.agent.InvocationResult;
import ai.tuvium.experiment.agent.TerminalStatus;
import java.util.List;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Placeholder AgentInvoker implementation. Replace this with your domain-specific
 * invoker that wraps AgentClient and implements the actual agent interaction.
 *
 * <p>This placeholder logs the invocation and returns a successful no-op result,
 * allowing the experiment loop to be tested before the real agent is wired in.</p>
 *
 * <p><strong>To customize:</strong></p>
 * <ol>
 *   <li>Rename this class to {@code {Domain}AgentInvoker}</li>
 *   <li>Inject an {@link org.springaicommunity.agents.client.AgentClient}</li>
 *   <li>Implement domain-specific pre/post processing</li>
 *   <li>Return real {@link InvocationResult} with token counts and cost</li>
 * </ol>
 */
public class TemplateAgentInvoker implements AgentInvoker {

	private static final Logger logger = LoggerFactory.getLogger(TemplateAgentInvoker.class);

	@Override
	public InvocationResult invoke(InvocationContext context) throws AgentInvocationException {
		logger.info("TemplateAgentInvoker invoked for workspace: {}", context.workspacePath());
		logger.info("Prompt length: {} chars", context.prompt().length());
		logger.info("Model: {}", context.model());
		logger.warn("This is a placeholder — replace with your domain-specific AgentInvoker");

		long startTime = System.currentTimeMillis();

		// Placeholder: return a successful no-op result
		return InvocationResult.completed(
				List.of(),  // phases
				0,          // inputTokens
				0,          // outputTokens
				0,          // thinkingTokens
				0.0,        // costUsd
				System.currentTimeMillis() - startTime,
				null,       // sessionId
				context.metadata()
		);
	}

}
