# The Word panel replies to, resolves and adds comments (partly shipped)

Why: second part of #473, after accept and reject (#477).

## Shipped
- A comment card in the rail, once picked, has a reply box (Ctrl+Enter sends) and Resolve / Reopen
  for the thread. Selecting words on the page opens a bar to comment on them. Each action posts one
  operation to `POST /api/threads/{id}/docx-review` (`reply`, `resolve`, `reopen`, `comment`), then
  the panel re-reads the file, keeps the scroll and shows the server's reason when it refuses (for
  example words that appear twice).
- `replyTo`, `setResolved` and `commentOn` in `lib/docxReview.ts` (unit tested); the card moved to
  `DocxCommentCard.tsx`, the selection bar is `DocxNewComment.tsx`.
- `docx-review.spec.ts` gained a spec for reply, resolve, reopen, a comment on selected words and a
  refused comment. Broken on purpose (resolve and reopen swapped, the selection not folded) the
  tests fail.

## Not verified
- Real Word opening the saved file, and the Windows desktop app.
- A selection that crosses formatting runs may not match one run; the server's reason is shown.

## Follow-ups
- Deleting your own comment: `_review.py` has no operation for it (asked on #473).
- The reviewer name in Settings and "Ask coscribe" on a selection (#473).
