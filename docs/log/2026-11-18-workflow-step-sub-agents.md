# A workflow's high or full agent step hands parts of its task to sub-agents (shipped)

Why: decision 0028 gives an L3 step "the environment's tools and sub-agents", but a step's agent
couldn't start one (`2026-10-29-workflow-agent-step-sub-agent.md`). Part of #843, the first of
its two open items. Decision 0051 (proposed) says how they run.

## Shipped
- `runtime_lg/workflow_sub_agents.py` (new): the step's own `spawn_agent`. A sub-agent runs in
  the foreground, on the step's model, with the step's tools and none to start sub-agents of its
  own. Its calls go through the step's allowlist, read-only rule, hooks, approval mode and audit
  log; one the step would ask a person about is refused with a note to report it, and the step's
  agent makes it itself, which pauses the run as before. It leaves a `turns.jsonl` line
  (`kind: subagent`, with the step's key).
- `runtime_lg/workflow_agent.py`: the tool is on every agent step's list (0001); a bounded step
  is refused it, and a high or full one may start 4 per pass, counted from the checkpoint. The
  step's record counts the sub-agents' calls, tokens and tools, and `sub_agents`.
- `runtime_lg/token_limit.py`: a sub-agent's tokens come back with its report and count where it
  was started, so the step stops at its 0043 budget for both; each sub-agent gets what is left.
- `workflows`: `AgentRequest.sub_agents`, `AgentReply.sub_agents`, `SUB_AGENT_TOOL`; a high or
  full step's task says it may delegate and that a call needing a person is its own.
- The run page's agent step row says how many sub-agents it started ("5 tool calls, with 2
  sub-agents"; `WorkflowAgentActivity.sub_agents`).
- Seven tests in `tests/test_workflow_agent_runner.py`, on a real LangGraph agent with a scripted
  model, and one for the row's words.

## Not verified
- On Windows, in the app, or with a real model: whether a model delegates when it should, and
  what that costs.

## Follow-ups
- The run page could show each sub-agent's report; only their number is shown.
