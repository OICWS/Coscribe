# A workflow's agent step runs as a sub-agent of the run's conversation (P1b part 2 of #719; partly shipped)

Why: part 1 had the engine run an agent step through a runner it is given; nothing gave it one.
This part is that runner, so a saved workflow's agent step runs, while `workflows` still imports
no agent runtime.

## Shipped
- `runtime_lg/workflow_agent.py`, `WorkflowAgentRunner`: the agent is built like a sub-agent,
  with the same tool list (0001) minus the code module and the tools that need a person; it is
  kept in the conversation's checkpointer under the step's key, and runs in a fresh context so
  its interrupts don't stop the workflow's graph. Every call comes to an interrupt, where the
  step's rules, the person's PreToolUse hooks and the audit log (`workflow_step`, `human`,
  `hook_veto`) apply. Answers to several calls in one message are kept on disk until all are in.
  A run out of steps still reports (`wrap_up`); a model that goes silent fails the step.
- `runtime_lg/subagents.py`: the helpers the runner shares are public there (`stream_turn`,
  `wrap_up`, `for_subagents`, ...); nothing else changes.
- `conversation`: `workflow_context` gives every run, and every test run, this runner and the
  tools that bring in outside content (`workflows.brings_outside_content`, now shared with the
  permissions route); a scheduled run passes its task's approval mode.
- The import contract is renamed "Workflows depend on no agent runtime" and covers all of
  `coscribe.workflows` and `coscribe.workflow_spec`. `runtime_lg`'s interface grows by one name
  (`WorkflowAgentRunner`; the ratchet baseline is raised by one).

## Measured
- Live on `deepseek:deepseek-flash`: a bounded step (`list_files`, `read_file`) counted two
  urgent mails of three with its fields right, a check passed, and a high step paused on
  `write_file`, went on once approved and wrote the file. About 34k input tokens per model call
  (the full tool list), 99% read from the provider's cache; 12 s for the run.

## Not verified
- On Windows, and in the app: no UI shows an agent step yet (P2).
- A step's cost cap (0028 says step and cost caps): only the step cap (`max_steps`) exists.
- An L3 step delegating to sub-agents: a step's agent can't start one.

## Follow-ups
- P2 the read-only canvas, with the agent step's card and its pending call; then P3 drafting
  (`docs/plan.md` item 8).
