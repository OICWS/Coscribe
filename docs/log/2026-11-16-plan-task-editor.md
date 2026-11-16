# The task list of a plan under review is edited in the Plan panel (shipped)

Why: part 2 of #901. The server takes an edited task list with a plan's answer
(`docs/log/2026-11-15-plan-review-edits.md`); the person needed a place to edit it.

## Shipped
- While a plan waits for an answer, the Plan panel's Tasks section is an editor
  (`components/PlanTaskEditor.tsx`): untick a step to leave it out, reword it, move it up or down,
  delete it, add one (Enter in the last step adds the next). The plan document stays on top and the
  steps sit at the bottom, under a divider. The panel opens by itself when a plan arrives.
- The draft is kept per plan (`lib/planTaskDraft.ts`); Accept, Accept and use auto mode and Revise
  send it as `tasks` when it differs from the model's list. Accepting shows the approved list at once
  (`approvedList`, the same numbering as `TaskToolkit.replace`, since a live turn sends no result
  for `exit_plan_mode`); a replayed history reads the server's list after `Task list as approved:`
  (`state/reducer.ts`). The task card and the Plan panel follow that list.
- The plan card shows the plan's title and says when the list was changed. Its main button is
  "Accept and use auto mode", also Ctrl+Enter outside a text field. "Accepted" replaces "You'll
  approve each change", which was wrong outside Plan mode.
- A panel in its own window edits the same draft (`planSteps` action).
- `App.tsx`'s plan wiring moved to `lib/planState.ts` (1084 to 1071 lines).
- Checked: vitest 459 tests; the six Plan e2e specs against the stub model, including the new one
  that edits, accepts and reloads to find the server's list.

## Not verified
- Windows, and a detached Plan window in the Electron app.
- A real model carrying out the edited list.

## Follow-ups
- Drag to reorder (buttons only for now).
