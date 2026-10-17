# Word review routes for the viewer (shipped)

Why: the Word viewer panel (decision 0014, `docs/assessments/2026-10-17-file-viewers.md` §3)
reads and acts on a file's review through the same functions the model's tools use.

## Shipped
- `GET /api/threads/{id}/docx-review?path=`: what `read_docx_review` returns.
- `POST /api/threads/{id}/docx-review` with `{path, operations}`: what `edit_docx_review` does,
  all or nothing; a bad operation answers 400 with the reason.
- `GET /api/threads/{id}/docx-review/original?path=`: the file with every tracked change rejected,
  for the Original view (docx-preview has no such mode).
- Actions from the panel carry the computer's user name, as Word does until a name is set.
- They run under the same per-file lock as the model's Word tools, within the conversation's
  folders. Test in `tests/web/test_threads.py`; `tests/openapi.json` updated.

## Not verified
- The user name on Windows (`getpass.getuser()`) shown in Word's comment pane.

## Follow-ups
- A reviewer name in Settings.
- The Word viewer panel (step 3).
