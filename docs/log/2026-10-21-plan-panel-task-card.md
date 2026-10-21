# The task list as a live card and a Plan panel (partly shipped)

Why: #506, PR 1 of 4 (design note: `docs/assessments/2026-10-21-plan-panel.md`). A plan that runs showed a sentence, a pile of command rows, another sentence; the task list lived only in the sidebar.

## Shipped
- `lib/taskCard.ts`: `taskListOf` replays `task_create` / `task_update` / `task_list` (from their results, from their arguments while a call is still running); `foldTaskCard` replaces, per turn, the stretch from the first task call to the last call by one card. The narration and calls of the stretch are not drawn (they stay in the history, so a reload rebuilds the card the same way); an approval waiting on the person, a question and the like stay in the transcript; the reply after the last call stays once the turn is over or the list is done. A failed call marks the item it ran under. A later turn that only updates the list draws the whole list (`Turn.tasksBefore`).
- `components/chatlog/TaskCard.tsx`: the card (filled tick, dots, dashed circle); an item opens to its calls, drawn with the rows from #505. `components/TaskList.tsx` is the list the Plan panel shares.
- `components/PlanPanel.tsx`: a new panel `plan` beside Browser and Background tasks (dock, pop-out window, desktop allow-list), with its switch (the checklist icon) shown once there is a plan or a task list. It shows the plan last proposed and the tasks.
- `TaskPanel`'s Progress becomes "N of M done" and an "Open plan" button while a task list exists; without one it is as before.
- `App.tsx` got shorter (1067 to 1056 lines): the panel list and the switches are driven by `PANEL_IDS` and one `panelOpen` function.
- Unit tests for the replay and the fold; `plan-panel.spec.ts` against the stub model.

## Not verified
- Not run on Windows, in the desktop shell (pop-out of the Plan panel) or in the packaged app.
- The stub model makes one call per message, so a single turn holding a whole list and its commands was exercised in unit tests, not live.

## Follow-ups
- #506 PR 2 to 4: the proposal card (Reject, Revise, Accept, Accept and auto mode, Open plan), the diff of a changed plan, a comment on selected text.
