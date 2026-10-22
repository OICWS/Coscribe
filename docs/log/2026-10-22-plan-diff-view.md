# The plan as a diff (partly shipped)

Why: #506, PR 3 of 4. A revised plan was a second card with the whole text again; the reference shows what changed.

## Shipped
- `lib/lineDiff.ts`: a line diff (longest common run of lines), the changed span inside a replaced line, "+N -M", and the rows near a change with a gap row for the rest.
- `components/PlanDiff.tsx`: a row above the proposal card, "Created plan +N" for the first plan and "Updated plan +N -M" after a revision; it opens to the lines with their numbers, red and green rows, and the changed words marked.
- A plan item carries `previous`, the plan proposed before it (set when it arrives live and when a history is replayed), so a reloaded conversation shows the same diff.
- Unit tests for the diff and for `previous`; `plan-proposal.spec.ts` revises a plan and opens the diff.

## Not verified
- Not run on Windows or in the desktop shell.
- A plan of several hundred lines is diffed in the browser with a quadratic table; plans are far shorter, so it was not measured.

## Follow-ups
- #506 PR 4: a comment on selected text in the Plan panel, sent inside Revise.
