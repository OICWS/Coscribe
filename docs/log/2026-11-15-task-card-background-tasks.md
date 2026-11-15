# The task card shows the background tasks each item started, again (shipped)

Why: the last open part of #598. The task card that follows its changes down the conversation
(`docs/log/2026-11-06-task-card-follows.md`) dropped what #600 and #603 had added: which background
agent or script an item started, and its state. The maintainer asked for it back on 2026-11-15.

## Shipped
- `frontend/src/lib/taskCard.ts`: `taskCardPlaces` replays every call of the conversation, not
  only the task calls, and binds a background task to the item in progress when it started (the
  one that started last, when several run). A task counts once its call's result is in: the three
  starters (`spawn_agent_background`, `run_background_script`, `run_background_command`) and a
  script that moved to the background at its time limit or when the person wrote mid-turn
  (`status: running_in_background`). A starter that needed approval carries its result on the
  approval item, which #600 did not read. `TaskCardEntry.bound` holds the tasks by item.
- `frontend/src/components/chatlog/TaskCard.tsx`: under an item, one line per task it started,
  "Background task · running" (or done, failed, needs approval, timed out, stopped), which opens
  the Background tasks panel on that task. A task waiting for approval shows the item as waiting;
  a failed or timed-out one adds "A background task failed". The states come from the
  `BackgroundTasks` context `App.tsx` already provides.
- No tool, prompt or wire change.
- Tests: `src/lib/taskCard.test.ts` (starters with an object, a JSON string and an approved call,
  a script moved to the background and one that ran to its end, no result yet, no item in
  progress, two items in progress, a later turn) and `tests/e2e/plan-panel.spec.ts` (an item lists
  the script it started and opens it, against the stub model).
- `docs/plan.md`: the Plan card item is done and taken out.

## Not verified
- A real model's conversation: which item a task goes to is inferred from time order, so a model
  that starts a task before it marks the item in progress puts it under the wrong one, or none.
- A real Windows machine.
