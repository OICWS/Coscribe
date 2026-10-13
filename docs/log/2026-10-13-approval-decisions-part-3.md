# The approval decision as a table, part 3 (shipped)

Why: after a call is decided, `ChatSessionLG._decide_action_request` also builds the approval
card and writes the audit record. Splitting `conversation/session.py` must not change either
(issue #103, last part).

## Shipped
- `tests/test_approval_records.py`: 33 cases through the real method with a fake socket and a
  recording page renderer (no LibreOffice).
  - `PREVIEW_ROWS` (15): a document or workbook edit carries a before and an after picture,
    both of the page named by a positive integer `slide` and of page 1 otherwise; a failed dry
    run keeps the before picture; no picture for a missing file, a path outside the workspace,
    a path that is not text, no path, an extension without a toolkit, a private method or a
    name that is not a method; nothing is rendered for an unattended run. The real file is
    unchanged, the dry run gets the same arguments on a copy, and the temporary copy is removed.
  - The card's fields (`id`, `tool_name`, the arguments as given, both pictures, the
    reviewer's note) and that two cards have different ids.
  - `RECORD_CASES` (13): the audit record for each reason keeps its explanation (a hook's
    message, plan mode's text, an exec rule's justification, the reviewer's reason, why nobody
    was asked) or none (human, pre-approved, Accept Edits, a run that skips approval); the thread,
    the tool, the decision and a timezone-aware timestamp are always kept, and secret-shaped
    arguments and details are blanked. A stop and a call that is not gated leave no record.

## Mutation check
Fifteen changes to `session.py` and `runtime_lg/audit.py` were tried, each reverted; fourteen
failed 1 to 13 named rows: the page chosen by `slide`, the temporary copy left behind, a failed
dry run losing the before picture, a private method previewed, the extension matched in one
case, a missing file previewed, the card without arguments, a dropped hook, exec-rule,
unattended or reviewer explanation, a wrong thread id, and arguments or details not redacted.
The fifteenth (building the picture for an unattended run) changes nothing: an unattended run is
refused before the card is built, so that condition cannot be reached.

## Not verified
- A real render by LibreOffice is covered by the existing `real_libreoffice` tests in
  `tests/web/test_threads.py`, not here.
