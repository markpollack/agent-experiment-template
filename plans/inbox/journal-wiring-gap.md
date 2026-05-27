# Gap: WorkflowAgentInvoker missing journal integration

> **Filed**: 2026-05-27
> **Resolved**: 2026-05-27
> **Source**: security-remediation-agent bootstrap (~/projects/experiments/security-remediation-agent)
> **Severity**: ~~Template gap — every consumer project must manually wire journal logging~~ **Fixed**

## Problem

`WorkflowAgentInvoker` in the template creates a `Workflow` and runs it, but does not wire a `WorkflowExecutor` with `WorkflowJournal.forRun(run)`. This means:

1. No agent-journal output by default for workflow-based experiments
2. Every consumer project must independently discover and wire the journal integration
3. The Markov analysis scripts (`make_markov_analysis.py`) depend on journal data to classify tool-call states — without journal wiring, Phase 0 state taxonomy discovery cannot run

## Current template code (no journal)

```java
// WorkflowAgentInvoker.java — current
ClaudeStep claudeStep = ClaudeStep.of("{input}")
    .workingDirectory(context.workspacePath())
    .permissionMode(PermissionMode.BYPASS_PERMISSIONS);

String result = Workflow.<String, String>define("experiment-run")
    .step(claudeStep)
    .run(context.prompt());
```

## What it should do

```java
// WorkflowAgentInvoker.java — with journal
WorkflowJournal.registerEventType();  // once at static init

try (Run run = Journal.run("experiment-run").start()) {
    ClaudeStep claudeStep = ClaudeStep.of("{input}")
        .workingDirectory(context.workspacePath())
        .permissionMode(PermissionMode.BYPASS_PERMISSIONS);

    WorkflowExecutor executor = new WorkflowExecutor(
        new LocalStepRunner(),
        WorkflowJournal.forRun(run));

    Workflow.<String, String>define("experiment-run")
        .withExecutor(executor)
        .step(claudeStep)
        .run(context.prompt());
}
```

## Additional imports needed

```java
import io.github.markpollack.journal.Journal;
import io.github.markpollack.journal.Run;
import io.github.markpollack.workflow.flows.workflow.LocalStepRunner;
import io.github.markpollack.workflow.flows.workflow.WorkflowExecutor;
import io.github.markpollack.workflow.journal.WorkflowJournal;
```

## Dependencies already present

`workflow-journal` is already declared in the template `pom.xml` (`${agent-workflow.version}`), and `journal-core` + `claude-code-capture` are there too. No POM changes needed — just the Java wiring.

## Workaround

The security-remediation-agent project created `SecurityRemediationInvoker` that extends `AbstractTemplateAgentInvoker` and wires the journal manually. This is what every consumer will need to do until the template is fixed.

## Recommendation

1. Update `WorkflowAgentInvoker` to wire journal by default
2. Add `WorkflowJournal.registerEventType()` to a static initializer
3. Consider making the run name configurable (passed from `ExperimentConfig.experimentName()`)
