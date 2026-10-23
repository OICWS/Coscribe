# A sent file stays in the conversation as a card (shipped)

Why: after a person attached files and sent, the conversation showed no trace of them live, and
after a reload the raw "attached files" note text appeared inside the bubble.

## Shipped
- `runtime_lg/messages.py`: `split_attached_files(text)` takes the note off a user message and
  returns the text and the paths; history entries for user messages carry `files`
  (`UserEntry.files` in `conversation/wire.py`, `wire.gen.ts` regenerated).
- Frontend: a user message with files shows a card per file above the bubble, live and after a
  reload. Images and PDFs open in the preview dialog, Word, Excel and PowerPoint files open in
  their panel, other files show a card with the name and a type badge that does not open.
- A message of only attachments shows no empty bubble. Editing a message keeps its files: the
  note is appended again on submit.
- Tests: `tests/test_runtime_lg_messages.py`, `frontend/src/state/reducer.test.ts`,
  `frontend/tests/e2e/attachment.spec.ts` (live cards, reload, PDF dialog).
- Ratchet accepted small growth in `UserMessageView`, `Composer`, `App`, the reducer and
  `serialize_history_for_ws_lg`.

## Not verified
- Windows and the desktop app.
- Previews of file types beyond image, PDF and Office files (they show a card only).

## Follow-ups
- None.
