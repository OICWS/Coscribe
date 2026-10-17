# `conversation/session.py` agent assembly moved out (shipped)

Why: #348 item 4. `session.py` was 1,472 lines with 30 direct module imports; the goal was at most 1,300 lines and 25 imports.

## Shipped
- `conversation/agent_assembly.py` (new): `AgentAssembly` holds the tool list (`build_lg_tools`), the agent build (`build_lg_agent`), the deferred-tool decision (`tool_binding`) and the context panel's measurement (`context_breakdown`); `risks_of_gated_tools` is a module function. `ChatSessionLG` keeps one-line delegates for the names tests call.
- `conversation/subagents.py`: `SubAgentReporter.listen()` registers the background-task and inbox listeners that `ChatSessionLG.__init__` used to register itself.
- `session.py`: 1,472 to 1,279 lines, 30 to 25 imports; the `notify_resync` docstring lost its history narration.
- `tests/test_code_agent.py` patches `code_service` where it is now used.
- `quality/baseline.json` updated with `--accept-worse`: the deep-import keys moved with the code (`session` lost 5 keys, `agent_assembly` and `subagents` gained 5), and the total stays 37.

## Not verified
- `tests/` for conversation, code agent and web pass locally; no real conversation with a model was run in the desktop app.

## Follow-ups
- `ChatSessionLG.__init__` is still 206 lines.
