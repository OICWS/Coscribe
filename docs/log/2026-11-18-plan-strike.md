# Finished plan steps are struck through, and a long plan shows five steps (shipped)

Why: the plan card in the conversation only greyed a finished step, so done and open steps
were hard to tell apart at a glance, and a long plan filled the screen.

## Shipped
- The task card (`components/chatlog/TaskCard.tsx`): a finished step is greyed and struck
  through; resting the pointer on it lifts the line so it reads plainly. The Plan panel's list
  (`components/TaskList.tsx`) lifts its line on hover too.
- A plan of more than five steps shows five, starting three finished steps above the first
  open one, with "Show N more" to open the rest ("Show less" closes it). The folded
  "N steps done" line still opens to the whole list.
- Tests: `TaskCard.test.tsx` (strike classes, the five-step window); `taskCard.test.ts` pins
  where the card goes when the person sends a note mid-plan (it stays above the note until the
  model next changes the list, then moves below it; tasks made for the note join the same list).
- Live run on DeepSeek (`deepseek-flash`): a 6-step plan, two unrelated notes sent while it ran.
  The model read both before its next step, added the second as step 7 of the same list,
  answered the first at the end; the card moved below the notes at the next `task_update`.

## Not verified
- On Windows in the desktop app (checked in headless Chromium on Linux).
- Hover has no touch equivalent; on a touch screen the line stays.

## Follow-ups
- One task list per conversation, never cleared: an unrelated later request appends to a
  finished list (in `docs/plan.md`).
