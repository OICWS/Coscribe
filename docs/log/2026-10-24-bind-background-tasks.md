# The task card knows which background tasks an item started (partly shipped)

Why: part 3 of #598. The card cannot show a background task's real state on its item until it
knows which task belongs to which item.

## Shipped
- `foldTaskCard` fills `TaskCardEntry.bound`: the `task_id` returned by `spawn_agent_background`,
  `run_background_script` and `run_background_command`, under the item in progress when it started.
  Rebuilt from the saved history by the same rule (unit test over the same items).
- No UI change, no tool, prompt or wire change.

## Not verified
- The binding is inferred from time order, so a task can sit under the wrong item when the model
  returns to an earlier one. Not tried on a real conversation.
- The path that moves a running script to the background does not go through these tools; it is not bound.

## Follow-ups
- Part B of #598: show the bound tasks' state (waiting on approval, failed) and open the Background
  tasks panel from the item (`focusTaskId`). It needs the full task list (`loadBackgroundEntries`),
  not `useRunningBackgroundTasks`, which keeps only counts of the running ones.
