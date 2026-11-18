# 0051: A workflow step's sub-agents keep its rules and never wait for a person

Status: accepted (2026-11-18, by the maintainer; proposed the same day by OICWS in #954).
Narrows 0028: how an L3 step's agent uses sub-agents. Counts their tokens under 0043's step
budget. Part of #843.

## Context
0028 gives an L3 step (`autonomy: high`, and `full` above it) "the environment's tools and
sub-agents", but a step's agent could not start one: a conversation's `spawn_agent` answers its
sub-agents' approvals from the Sub Agents panel and reports to the conversation, and a workflow
run has neither. A step's agent pauses for a person through its checkpoint, which survives a
restart; a sub-agent's state lives only as long as its call.

## Decision
- **High and full steps may start sub-agents; bounded ones may not.** A bounded step's allowlist
  is its consent (0028), so its `spawn_agent` call is refused. The tool is on every step's list,
  so the list stays the same (0001).
- **Each pass of a step starts at most 4** (`MAX_SUB_AGENTS`), in the foreground: the step waits
  for each report. Counted from the checkpoint, so a resumed pass doesn't start more.
- **A sub-agent keeps the step's rules.** Its calls go through the same allowlist, read-only rule
  (untrusted input), test-run confirmation, PreToolUse hooks, approval mode and audit log as the
  step's own. It runs on the step's model and gets the step's tools, never `spawn_agent`.
- **It never waits for a person.** A call of its that the step would ask a person about is
  refused, with a note to say so in its report; the step's agent makes that call itself, and
  that call pauses the run as before.
- **Its tokens are the step's.** Its report carries what it used (`tokens_used` counts it where
  it was started), so the step stops at 0043's budget for both; each sub-agent may use what is
  left when it starts. The step's record counts its calls, tokens and tools, and `sub_agents`.
- **No panel, no words kept.** It does not show in the Sub Agents panel; it leaves a line in
  `turns.jsonl` (`kind: subagent`, with the step's key; 0045).

## Consequences
- `AgentRequest` gains `sub_agents`, `AgentReply` gains `sub_agents`; `runtime_lg` adds
  `workflow_sub_agents.py`; `workflows` exports `SUB_AGENT_TOOL`.
- Under a task's manual approval mode a sub-agent can only read: everything else is the step's.
- A sub-agent cut off by a restart is lost with its work, as any call running then is.
- Not done: a sub-agent on another model, or one running in the background.
