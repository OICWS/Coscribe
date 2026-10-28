# A workflow run waiting for the browser says so (shipped)

Why: after "Let AI look into it", the assistant's test runs hold the one browser lock. A re-run started meanwhile queued silently: no steps, no sign why. The run page also lost the way back to the investigation once the run was no longer failed.

## Shipped
- `ScheduledRun.queued`: set while a browser workflow run waits for `BROWSER_RUNS`, cleared when it starts, finishes or is reopened.
- The run banner shows "Waiting for the browser -- another run or test is using it".
- The run page keeps a link to the investigation conversation for runs that are no longer failed.

## Not verified
- Not run in the desktop app on Windows; covered by a store test and the frontend build only.

## Follow-ups
- Browser tabs are shared by all conversations (one panel, one partition); per-conversation tabs would allow parallel runs.
