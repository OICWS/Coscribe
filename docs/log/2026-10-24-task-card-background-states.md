# The task card shows the state of the background tasks an item started (shipped)

Why: part 3 of #598. An item that started a background agent or script now shows what that task is
doing, instead of only what the model last wrote on the list.

## Shipped
- A task of the item waiting for approval shows the item as waiting (ring with three dots); a failed
  or timed-out one adds "A background task failed" to the item.
- An opened item lists its background tasks with their state; one click opens the Background tasks
  panel on that task.
- The states come from the list `useRunningBackgroundTasks` already holds (it keeps finished tasks
  too; it only returned the counts before), through the `BackgroundTasks` context.
- No tool, prompt or wire change.

## Not verified
- No Playwright spec or screenshot, no run in the real app or on Windows. The component has no unit test;
  the binding it reads is tested in `taskCard.test.ts`.
- Stopped tasks are not marked as failed, on purpose.

## Follow-ups
- A Playwright spec against the stub model with before/after screenshots.
