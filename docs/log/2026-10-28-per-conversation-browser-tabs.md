# Each conversation and workflow run has its own browser tabs (partly shipped)

Why: all conversations shared one set of tabs, so the backend let only one browser workflow run or test go at a
time (`BROWSER_RUNS`); a re-run waited behind a test with no progress, and multi-threaded work could not use the
browser together (issue #688).

## Shipped
- `browserPanel.ts`: every tab belongs to a group (the thread id). The panel shows the group the open conversation
  names (`browser-panel:view-group`); other groups' active tabs stay attached off-screen and keep working. The
  cookie partition `persist:coscribe-browser` is still shared, so a sign-in is done once. `MAX_TABS` is per group.
- `browserAgent.ts`: steps queue per thread instead of globally, a step finds its own stop flag through an async
  context (the single `running` slot is gone), and the agent frame timer is per thread. Tab commands act on the
  calling thread's group only.
- `tools/web/browser.py`: `BROWSER_RUNS` is replaced by `browser_run(thread_id)`, a lock per thread, so runs in
  different threads go side by side and two in one thread still take turns.

## Not verified
- The desktop app on Windows: two conversations driving the browser at once, switching conversations while
  another one works, popups and downloads landing in the right group.

## Follow-ups
- A group's tabs are closed only at app quit; close them when a run's thread is finished.
- PR #687's "Waiting for the browser" state now only shows for runs inside one thread.
