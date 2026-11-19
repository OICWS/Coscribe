# A new plan starts its own task list once the last one is done (shipped)

Why: a conversation had one task list that was never cleared, so an unrelated request after a
finished plan was added to it (a live DeepSeek run showed "10 steps done" for a 3-step request
that followed a 7-step one).

## Shipped
- `task_create` (`tools/bookkeeping/tasks.py`): when every task in the list is completed, the
  new task starts a new list. Ids keep counting, so a stale `task_update` on an old task fails.
  A task made while any task is open still joins the list.
- The conversation's replay (`frontend/src/lib/taskCard.ts`) does the same: the finished list
  keeps its "N steps done" line where it finished, and the new list gets a card of its own. The
  Plan panel shows only the new list.
- Tests: `tests/test_task_tools.py` (new list after a finished one, join while open);
  `taskCard.test.ts` (two cards, each with its own items).
- Live run on DeepSeek (`deepseek-flash`): two unrelated 3-step requests in one conversation
  show "3 steps done" twice, and the state file holds only the second list (ids 4-6).

## Not verified
- On Windows in the desktop app (checked in headless Chromium on Linux).

## Follow-ups
- A note sent while a plan is open still joins it when the model makes tasks for it (in
  `docs/plan.md`).
