# The task card shows items running in parallel (shipped)

Why: the card drew one item as in progress and filed every call under the first one, so work that
runs side by side (a background agent beside a script) looked like a strict 1-2-3.

## Shipped
- `TaskStatusIcon`: a spinner means running, so two spinners are two items in parallel; a ring with
  three dots means stopped on the person (an approval or an `ask_user_question` answer); a dashed circle means not started.
- `foldTaskCard`: calls are drawn under the in-progress item that started last (it used the first);
  `TaskCardEntry.waiting` lists in-progress items with a pending approval or question. Which item a call belongs to is inferred from time order, not a fact.
- No tool schema or prompt change, so the provider cache is untouched. Unit tests in `taskCard.test.ts`.

## Not verified
- No Playwright spec or screenshot against the stub model; not seen in the running app or on Windows.
- The Plan panel list shows spinners but not the waiting state (it has no approvals).

## Follow-ups
- Dependencies (`blocked_by`) and linking an item to its background task need a tool change; a
  decision record first (one-time cache invalidation on release is accepted by the maintainer).
