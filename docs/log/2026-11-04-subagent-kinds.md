# spawn_agent takes a ready-made role: research or check (shipped)

Why: every delegation's role and tool set were written on the spot by the coordinator, so a
sub-agent sent to look something up got every tool, writers included, and a role of a line or
none. Claude's Agent SDK defines sub-agents the same way: a description, a prompt and a tool set
chosen once.

## Shipped
- `runtime_lg/subagent_kinds.py`: `research` (finds things in files and on the web, reports each
  with its source; tools whose risk is READ) and `check` (confirms given figures and statements
  against their sources; READ and EXEC, so a script can recompute a figure, approved as always).
  Connector tools are EXTERNAL, so neither kind gets them unless named.
- `spawn_agent` / `spawn_agent_background` take `kind`. The call's own `instructions` replace the
  kind's role and its `tool_names` replace the kind's tools. Both tools share one argument list
  in their descriptions now, built where it was patched for the configured models.
- Tests: `tests/test_subagent_tasks.py` (a research run is told its role and gets only READ tools;
  own instructions keep the kind's tools; an unknown kind is refused).

## Not verified
- How often a real model picks a kind, and whether research runs in parallel save time: needs a
  live run on a real provider.
