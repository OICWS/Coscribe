# The engine runs an agent step through a runner it is given (P1b-1 of #719; partly shipped)

Why: decision 0028's agent step was in the spec (P1a) but refused at preflight. This part runs
it in the engine, against a runner `conversation` will supply, so `workflows` still imports no
agent runtime.

## Shipped
- `workflows/agent_step.py`: what the engine asks of a runner (`AgentRequest`, `AgentReply`,
  `AgentCall`, `AgentRunner`), which calls go ahead (the code module never; only READ calls
  when the step reads outside content; a bounded step's allowlist), how a gated call is decided
  (bounded: the allowlist was the consent; high and full: the task's approval mode as a prompt
  task has it, so "skip" approves all, "auto" a local change only, otherwise a person), and the
  step's fields from the agent's last reply (its closing JSON, or
  one model call reading them out of the report).
- `workflows.engine`: an agent step runs when `StepContext.run_agent` is set; preflight refuses
  it otherwise, and refuses an unknown, unavailable or code tool in its allowlist. A call that
  needs a person pauses the run with `interrupt()`; on resume the node asks the runner again
  under the same key (LangGraph's task id: stable across a pause, new on `retry_from`), so
  nothing the agent did runs twice. Each answer names its call, because a resume replays
  earlier answers by position. The step's run record gets `agent` (the pending call while
  waiting; tool calls, tokens and tools used when done).
- `workflow_spec`: `trusted_input` on an agent step lifts the read-only rule.
- `langgraph>=1.2.0` (the runtime's `execution_info.task_id`).

## Not verified
- No real runner yet: the tests use a scripted one. A real agent and a live model come in P1b-2.

## Follow-ups
- P1b-2: the conversation's runner (a sub-agent with the deferred tool list, the allowlist held
  at `use_tool` and the approval layer, its own checkpoint per key), the import contract
  renamed, live DeepSeek tests (`docs/plan.md` item 8).
