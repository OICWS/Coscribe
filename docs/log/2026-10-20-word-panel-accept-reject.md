# The Word panel accepts and rejects tracked changes (partly shipped)

Why: the maintainer lifted the pause on the Word panel's actions (#473). This is the first part:
tracked changes. Comments and the reviewer name follow.

## Shipped
- A bar above the page in the Review view: Accept and Reject for the change picked on the page (a
  click on it, or Previous / Next), and Accept all / Reject all behind a confirmation. The panel
  posts the operations to `POST /api/threads/{id}/docx-review`, re-reads the file and puts the
  scroll back; a refusal shows the server's reason and changes nothing. A call that waits on the
  per-file lock shows "Applying…".
- `settleChange` / `settleAllChanges` in `lib/docxReview.ts` (unit tested); the bar is
  `DocxChangeBar.tsx`, the hooks `docxActions.ts`.
- `frontend/tests/e2e/docx-review.spec.ts` on a generated file (`fixtures/build_redline.py`),
  added to `SPECS` in `e2e.yml`. Broken on purpose (accept and reject swapped, accept-all and
  reject-all swapped) it fails.

## Not verified
- Real Word opening the saved file, and the Windows desktop app.
- A change the page cannot match to the review (the counts differ) can't be picked; the bar then
  stays off for it.

## Follow-ups
- Comments (add, reply, resolve, reopen), the reviewer name in Settings and "Ask coscribe" on a
  selection (#473). Deleting your own comment needs an operation `_review.py` does not have yet.
