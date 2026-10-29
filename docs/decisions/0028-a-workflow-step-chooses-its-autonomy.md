# 0028: A workflow step chooses its autonomy; the graph stays fixed

Status: proposed (2026-10-29, kurtosisOC; needs the maintainer's acceptance). Narrows 0005: a
fixed run may contain an agent step, never the code module. Issue #719.

## Context
A scheduled task is either a fixed workflow (seven step kinds, no agent at run time) or written
instructions a fresh assistant works out each run. Nothing sits between them: a workflow that is
fixed for 19 cases in 20 fails on the twentieth, and an instructions task is slow, costly and
different every run. The limit is the spec, not LangGraph: `workflows/engine.py` already compiles
any spec into a `StateGraph` with interrupts and checkpoints.

## Decision
- **Autonomy is a property of a step, not of a task.** The graph (order, branches, loops,
  approvals) stays a fixed `StateGraph`; a step is one of: L0 fixed (tool, script, check), L1 a
  model call with no tools (`llm`, as now), L2 a bounded agent (a tool allowlist, step and time
  limits, an output schema, a check after it), L3 an agent with the environment's tools and
  sub-agents, L4 the whole task as one agent. A written-instructions task reads as one L4 step.
- **The AI picks the lowest level that works**, step by step, and proposes lowering a step whose
  runs have become the same calls every time.
- **A failure climbs one layer at a time, each with a limit**: the step's own exception handler
  (an agent that may finish that step only, to its output schema), then the investigation of the
  whole run (`start_investigation`), then the repair is proposed as a fixed branch and a test case.
- **Saving is still the consent.** Every change the AI makes is a proposal the person saves. An
  agent step declares the folders and sites it may touch; anything outside stops it. A step that
  read untrusted content (a page, a mail, an outside file) gets read-only tools by default.
- **`workflows` still does not import `runtime_lg`.** The agent runner is injected through
  `StepContext` by `conversation`; the import contract is renamed and keeps forbidding
  `runtime_lg`, `coordinator` and `code_runtime`.

## Consequences
- `Workflow.version` becomes 2; version 1 workflows load unchanged.
- The code module stays out of workflows (0005 unchanged on that point).
- Scripts and commands keep 0021 and 0022: an agent step gets no wider sandbox than a chat.
- An agent step's run is not repeatable as an L0 step is; its run record keeps its tool calls.
- Built in phases (#719): this record, the spec and runner, a read-only canvas, the drafting
  loop, the repair layers, then parallel steps, sub-workflows, triggers and state.
