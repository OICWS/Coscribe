# "Ask coscribe" on a selection in the Word panel

Why: last part of #473 (the reviewer name is #491).

## Shipped
- Selecting words in the Word panel shows an "Ask coscribe" button in the selection bar. It sends
  "Question about <file>, page <n>:" with the words quoted as a message to the conversation, so the
  model can find the place. `askMessage` in `lib/docxReview.ts` builds it (unit tested).
- The message goes through the same sender as Slides comments; with no link it is just sent, since
  there is no comment to post an answer back to. Detached panel windows send it through the
  existing `sendComment` window action.
- `docx-review.spec.ts` gained a step that checks the quoted question appears in the chat.

## Not verified
- Real Word and the Windows desktop app; the detached panel window path (only typed).
- The location is the page, not the nearest heading: docx-preview does not mark headings reliably.

## Follow-ups
- Deleting your own comment: `_review.py` has no operation for it (asked on #473).
