package com.example.experiment;

import java.util.List;

import io.github.markpollack.experiment.agent.InvocationContext;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Two-phase (explore + act) AgentInvoker stub. Uses ClaudeSyncClient for
 * session continuity across phases.
 *
 * <p>Phase 1 (Explore): Reads codebase and knowledge, creates a plan.
 * Phase 2 (Act): Executes the plan from Phase 1 in the same session.
 *
 * <p><strong>To implement:</strong></p>
 * <ol>
 *   <li>Use {@code ClaudeClient.sync()} to create a persistent session</li>
 *   <li>Send explore prompt via {@code client.connect(prompt)}</li>
 *   <li>Parse explore phase with {@code SessionLogParser}</li>
 *   <li>Send act prompt via {@code client.query(actPrompt)}</li>
 *   <li>Parse act phase and return both captures</li>
 * </ol>
 */
public class TwoPhaseTemplateAgentInvoker extends AbstractTemplateAgentInvoker {

	private static final Logger logger = LoggerFactory.getLogger(TwoPhaseTemplateAgentInvoker.class);

	private final String actPrompt;

	public TwoPhaseTemplateAgentInvoker(String actPrompt) {
		super();
		this.actPrompt = actPrompt;
	}

	@Override
	protected AgentResult invokeAgent(InvocationContext context) throws Exception {
		logger.info("TwoPhaseTemplateAgentInvoker invoked for workspace: {}", context.workspacePath());
		logger.info("Explore prompt length: {} chars", context.prompt().length());
		logger.info("Act prompt length: {} chars", actPrompt.length());
		logger.warn("This is a placeholder — implement two-phase invocation with ClaudeSyncClient");

		// TODO: Implement two-phase invocation:
		// try (ClaudeSyncClient client = ClaudeClient.sync()
		//         .workingDirectory(context.workspacePath())
		//         .model(context.model())
		//         .permissionMode(PermissionMode.DANGEROUSLY_SKIP_PERMISSIONS)
		//         .build()) {
		//     client.connect(context.prompt());
		//     PhaseCapture explore = SessionLogParser.parse(client.receiveResponse(), "explore", ...);
		//     client.query(actPrompt);
		//     PhaseCapture act = SessionLogParser.parse(client.receiveResponse(), "act", ...);
		//     return new AgentResult(List.of(explore, act), sessionId);
		// }

		return new AgentResult(List.of(), null);
	}

}
