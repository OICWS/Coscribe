# A script moves to the background at its time limit, or when the person writes mid-turn (shipped)

Why: part B of the stop and background plan the maintainer approved on 2026-11-06. `run_python_script` and `run_node_script` killed a script still running at its time limit (up to 600 s), and a note the person wrote while a script ran waited until the script ended, up to that whole limit, before the model read it.

## Shipped
- `tools/exec/running.py`:
  - A script still running at its time limit is handed to the background tasks, as the "Run in background" button does, instead of being killed. The tool result says it moved at its time limit, with the task id and the output so far; its end comes to the conversation as a report (#826).
  - A Python script that does nothing but sleep (imports, `sleep` calls and loops of them) still ends at its time limit: moving it would only hide the model waiting out time it should have spent ending its turn.
  - `request_detach` takes `None` for every script of the conversation, and a reason, which picks what the tool result tells the model (the person moved it, the person wrote to you, the time limit).
- `conversation/session.py`: a note written mid-turn moves every script the turn waits on to the background, so the model reads the note at its next step.
- `tools/bookkeeping/background_tasks.py`: the session's event loop is kept with its change listener, so a script handed over from a tool's worker thread at its time limit still announces itself and reports its end.
- Not changed: a workflow's script step (it has no conversation to hand over to, so it still ends at its time limit), command lines (they always run in the background), and approvals or sub-agents a turn waits on.
- The two tools' `timeout` argument says what now happens at the limit.
- Tests: `tests/test_run_in_background.py` (time limit, a sleep-only script, a note moving every script, what counts as only sleeping), `tests/web/test_chat.py` (a note mid-turn asks to let go of the scripts).

## Not verified
- A real Windows machine, and a script in the AppContainer reaching its time limit (it uses the same `RunningCommand` hand-over as the button).
- A Node script that only waits is moved like any other; only Python is recognised.

## Follow-ups
- A task that ends during the turn that started it is still reported only after that turn (from #826).
