# 0028: A workflow step chooses its autonomy; the graph stays fixed

Status: proposed (2026-10-29, kurtosisOC; needs the maintainer's acceptance). Supersedes 0005 in
part: a run may contain an agent step; the code module stays out. Issue #719.

## Context
A scheduled task is fixed steps with no agent at run time, or instructions an agent works out each
run; nothing sits between. The limit is the spec, not LangGraph: `workflows/engine.py` already
compiles a spec into a `StateGraph` with interrupts and checkpoints.

## Decision
- **Autonomy is per step; the graph (order, branches, loops, approvals) stays fixed.** L0 fixed
  (tool, script, check); L1 `llm`, no tools; L2 a bounded agent (tool allowlist, declared folders
  and sites, step and cost caps, output schema, a check after it); L3 an agent with the
  environment's tools and sub-agents; L4 the task as one agent. The AI picks the lowest level that
  works and proposes lowering a step whose runs repeat the same calls.
- **Consent.** L2: the allowlist and the declared folders and sites, shown at save time, are the
  consent; a call outside them parks the run as `needs_approval`. L3 and L4 run under the task's
  `approval_mode`, as a prompt task does now. Every AI change is a proposal the person saves.
- **Untrusted input, decided from the spec.** An agent step that references the output of a step
  reading outside content (browser, `http_request`, web search, a connector) gets read-only tools
  unless the person grants more at save time.
- **Tool list (0001).** The bound list stays the same; an agent step's allowlist is enforced
  where `use_tool` and the approval layer run the call, so the provider cache is kept.
- **Code module.** The runner's tool set never includes `run_code_task` or `run_code_command`,
  and a test holds it. Letting code into a run would need its own record.
- **Failures climb, each layer capped.** The step's exception handler (an agent that may finish
  that step only, to its schema: at most 3 attempts and 30 tool calls), then the run's
  investigation (`start_investigation`, once per run of the same failure, not every night), then
  the repair is proposed as a fixed branch plus a test case. The handler is off for version 1
  workflows and on, per step, in new drafts. Each run records what its agents cost.
- **`workflows` imports no agent runtime.** `conversation` injects the runner through
  `StepContext`. The contract keeps forbidding `runtime_lg`, `coordinator` and `code_runtime` and
  is renamed "Workflows depend on no agent runtime": it no longer means a run has no agent.

## Consequences
- `Workflow.version` becomes 2; version 1 workflows load and run unchanged. A prompt task reads
  as one L4 step; stored tasks are not migrated.
- An agent step is not repeatable as an L0 step is; its run record keeps its tool calls.
- P1 changes the import contract (an invariant path): it needs an independent review.
