# A running script row has a "Run in background" button (shipped)

Why: #510. The backend of the hand-over was in the pull request before this one; this is the button that uses it.

## Shipped
- A running `run_python_script` or `run_node_script` row (a lone call's header, or a row inside an opened run) shows **Run in background**. It sends `detach_command` with the script's text; the tool call returns, the turn goes on, and the script carries on as a background task (Background tasks panel, stop, log). The button is not shown in the Background tasks panel's own transcripts, for other tools, or for a finished call.
- `tests/e2e/run-in-background.spec.ts` (in the nightly list): approves a slow script against the stub model, clicks the button, sees the turn finish and the task still `running`.

## Not verified
- Windows and the desktop app.
- A script that ends in the moment between the click and the hand-over simply returns its result as before.

## Follow-ups
- Stopping the turn while a script waits does not kill the script (`docs/plan.md`).
