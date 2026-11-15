# A plan is reviewed before a large task, and the person's edits to its task list are carried out (partly shipped)

Why: a plan could be reviewed only in Plan mode, which few people turn on, and only taken whole,
rejected or sent back with feedback; dropping or rewording one step meant another round with the
model (#901).

## Shipped
- `exit_plan_mode` is no longer refused outside Plan mode: its description and the coordinator's
  instructions tell the model to record the steps with `task_create` and ask for review before a
  task of many steps, many files or one hard to undo, and to just do a small one.
  `tests/tool_schemas.txt` regenerated on Python 3.11 (system prompt +213 characters,
  `exit_plan_mode` +372).
- Accepting outside Plan mode keeps the current approvals; "auto" switches to auto mode (or keeps
  it). In Plan mode both answers behave as before. An unattended run still gets no review.
- A plan's `question_response` may carry `tasks` (`conversation/wire.py`, `PlanTaskEdit`): the
  list as the person left it. On approval `TaskToolkit.replace` makes it the plan's list (a kept
  id keeps its status, a new step gets an id past the old ones, a left-out step is gone) and
  `exit_plan_mode`'s result ends with `Task list as approved:` and that list as JSON, which the
  frontend reads back. With Revise the list is described in the feedback instead.
- `TaskToolkit` reads its file under the file's lock on every change instead of keeping the list
  in memory: the approval code writes the list through its own instance, and the tool's instance
  would otherwise have written its stale copy over it.

## Not verified
- A real model deciding when a task is large enough to ask for review: no run on a real provider
  here. Too many reviews would be the failure to look for.
- Windows.

## Follow-ups
- Part 2: the task list editor in the Plan panel and the card (#901).
- `task_update` rewording or dropping a step, `task_create` taking several steps, a background
  task started with its plan item (`docs/plan.md`).
