# The task card follows its changes down the conversation and folds when done (shipped)

Why: the maintainer asked for the plan card to behave like a live progress card: always under the newest content, moved only when its items change (not after every reply), and gone once the work is done, leaving one line that opens to the steps. Before, the card stood where the first task call of a turn was and replaced the calls and narration of that stretch, so later work scrolled past it.

## Shipped
- `frontend/src/lib/taskCard.ts`:
  - `taskCardPlaces` replays the task calls of the whole conversation and keeps only those that changed the list. The card goes under the last of them, so it follows the list across turns. A call that leaves the list as it was (a `task_list`, or an update to the same status) doesn't move it.
  - A list that was all done and then grew keeps its done line where it finished, and the new card goes under the newest change.
  - `foldTaskCard` takes the task calls out of their tool runs and puts the card where `taskCardPlaces` says; the other calls and the narration stay in the transcript as they are.
- `frontend/src/components/chatlog/TaskCard.tsx`: "Steps · N of M done" over the list while work is open; once every item is done, one line "✓ N steps done" that opens to the list.
- `frontend/src/lib/transcriptGrouping.ts`: `Turn.taskPlaces` (computed once per conversation) replaces the per-turn list carried into the next turn.
- `frontend/src/state/reducer.ts`: a tool result goes to the started call of the same tool with the same arguments, and only then to the newest one still open. Parallel calls of one tool (three `task_create` in one model reply) used to take each other's results, so the list showed in reverse order. The case moved out of `chatReducer` into `withToolResult`.
- Tests: `src/state/reducer.test.ts` (parallel calls), `src/lib/taskCard.test.ts` (placement, no move on an unchanged list, the done line, a grown list, a later turn, runs split around a task call) and `tests/e2e/plan-panel.spec.ts` against the stub model.

## Not verified
- A real Windows machine. Checked here with the stub model (e2e) and a live run with `deepseek:deepseek-flash`.

## Follow-ups
- The card no longer shows which background tasks an item started (from `docs/log/2026-10-24-task-card-background-states.md`); those tasks still show as their own rows and in the background panel. Bring it back on the card if it is missed (`docs/plan.md` item 3).
