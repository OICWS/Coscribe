# Tasks made in one answer keep the order the model wrote them (shipped)

Why: the replay of evaluation task 01 gave another result on Python 3.11 than on 3.13
([eval replay](2026-11-10-eval-replay.md)). Two things in it followed scheduling, not the
conversation.

## Shipped
- `runtime_lg/call_order.py`: `CallOrderMiddleware`. LangGraph runs the tool calls of one answer
  at the same time, so eight `task_create` calls got their ids in the order their threads ran:
  a recorded run listed the plan as reports 7, 4, 8, 3, 2, 1, 5, 6. Each `task_create` now waits
  for the one before it in the same answer (30 s at most). Other tools are not held. A real run
  after the change lists 1 to 8.
- `TaskToolkit.create` takes a lock around reading and raising the next id.
- The evaluation turns `prompt_suggestions` off. This, not the ids, is what made the replay
  differ: the suggestion is a background call that the next message cancels, and whether it was
  made at all depended on how the event loop ordered two tasks. The earlier log entry named the
  ids as the cause; that was wrong.
- Task 01 has a tape again, recorded after the change; it replays the same three times in a row
  on Python 3.11 and 3.13.
- `quality/baseline.json`: the two hook methods of the new middleware are added to the dead-code
  list, as `edit_guard.py`'s are (LangGraph calls them by name). `build_langgraph_agent` is two
  lines shorter.

## Not verified
- The plan card in the running app on Windows; the order is tested through the agent graph on
  both the sync and the async path (`tests/test_call_order.py`).

## Follow-ups
- Tasks 06, 07 and 09 (Office files) also replay the same on both versions with suggestions
  off, but take 15 to 20 s each because the delivery check renders the files, and they need
  LibreOffice on the machine. They fit a nightly job, not the PR checks.
