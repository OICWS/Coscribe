# A running script can be handed to the background tasks: the backend (partly shipped)

Why: a running `run_python_script` or `run_node_script` could only be waited out or timed out, and Stop ended the whole turn. #510 asks for a "Run in background" button on the running command; the design is `docs/assessments/2026-10-22-run-in-background.md`. This is the first of two pull requests: nothing in the UI sends the new message yet.

## Shipped
- `tools/exec/running.py`: the two script tools start the process themselves (`Popen`, its own process group on POSIX, stdin closed) and pump stdout and stderr on two threads, instead of `subprocess.run`. Without a detach the result is the same dict as before; a timeout now kills the whole process tree, not only the script.
- A registry of waiting commands keyed by the tool call's id, and `ToolCallIdMiddleware` (`runtime_lg/tool_call_id.py`) that binds that id around each tool call. Tests prove a sync tool sees it in both a blocking and a streamed turn on this LangGraph version.
- `detach_command {id}` on the chat socket (`wire.py`, types regenerated, `ws.py`, `ChatSessionLG.detach_command`). The tool call returns `{"status": "running_in_background", "task_id", "output_so_far", "note"}` at once.
- `adopt_running_command` (`tools/bookkeeping/background_tasks.py`): a `BackgroundTask` record and log for the live process, a watcher thread that settles it and announces to the event loop (`call_soon_threadsafe`), the 30 minute limit counted from the hand-over. The task shows in the Background tasks panel and stops through the same path as the others. After a detach the log is one stream in the order written.
- Tests: `tests/test_run_in_background.py` runs real short processes (exit, timeout, detach with output order and scratch cleanup, stop after detach, no hand-off), and `tests/web/test_chat_stop.py` sends the socket message.

## Not verified
- Windows: killing the process tree with `taskkill` and the pump threads on the packaged app.
- Stop of the turn while a script is still waiting does not kill the script yet (it did not before either); the design note's line about that is not built.
- No button yet: the live path from a click is only covered up to the socket message.

## Follow-ups
- PR 2: the "Run in background" button on a running script row, and a Playwright spec (`docs/plan.md`).
