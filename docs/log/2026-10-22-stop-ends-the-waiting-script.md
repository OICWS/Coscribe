# Stop ends the script a tool call is waiting on (shipped)

Why: Stop ended the turn but not the Python or Node script its tool call was still waiting on; the tool's worker thread sat on the process until it exited or timed out. The "Run in background" work (#510) left this open.

## Shipped
- `stop_commands(thread_id)` (`tools/exec/running.py`) kills the process tree of every script a conversation's tool calls wait on; the session calls it from `request_stop`. The tool call returns with the output so far. A script already let go on in the background is not waited on and is stopped from its panel.
- `tests/test_run_in_background.py` (a real process, only the stopped conversation's script ends) and a Playwright case in `run-in-background.spec.ts` (Stop during a slow script: the file it would write at the end is never written; shown to fail without the fix).

## Not verified
- Windows: the `taskkill` tree kill on the packaged app.
