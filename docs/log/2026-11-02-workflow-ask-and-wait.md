# A workflow run can ask you for values and wait for a time or a file (shipped)

Why: a run could stop only for an approval. A monthly task that needs a number only the person
knows, or the bank's file, had to be split in two or run by hand at the right moment (#776,
batch 3; decision 0033).

## Shipped
- `workflow_spec`: `AskStep` with `AskField` (typed values as inputs are, or a pick from a list
  before it; an optional timeout that fails or goes on with the defaults) and `WaitStep` (a
  duration, a time on a day, or a file with a longest wait). What later steps read from each
  (`scope.py`); neither is allowed after a failure. `input_value` turns "7" into 7 for a number.
- `workflows` (`pause_steps.py`): approval, ask and wait steps pause through one path; a run at
  a wait holds only its checkpoint. `WorkflowRun.wake()` continues a due run, `answer()` takes
  the values. A file counts once it has stopped changing for 5 seconds. A test run doesn't wait,
  and answers an ask with its defaults where it has them. The report lists the asks no one
  answered (`unanswered`); the drafter is told both kinds.
- Runs: a new run status, `waiting`, for a run at a wait step. Each poll
  (`poll_due_scheduled_tasks`, also behind `coscribe --check-wakes`) continues the paused runs
  that are due, so a run due while the app was closed goes on when it starts. The answer route checks values first (422 with why);
  stopping a waiting run ends it. A run waiting for an answer is announced and reminded once a
  day.
- Frontend: both kinds on the canvas, in the add menu, quick edit and the full editor
  (`PauseEditors.tsx`, `lib/pauseWords.ts`); the run view answers an ask on its card and shows
  when a wait ends, with Go on now or Check now (`PauseCards.tsx`); "Waiting" in the run lists.
- Tests: `tests/test_workflow_pauses.py` (22), `tests/web/test_workflow_pauses_web.py` (4),
  `lib/pauseWords.test.ts` (7), and the e2e spec `workflow-ask-and-wait.spec.ts`.

## Not verified
- On a real Windows machine: a wait that comes due while the app is closed, and a file wait on a
  synced folder (OneDrive) whose file appears in pieces.
- The desktop reminder for a run waiting for an answer, as the desktop app shows it.

## Follow-ups
- Batches 4 and 5 of #776 (in `docs/plan.md`).
