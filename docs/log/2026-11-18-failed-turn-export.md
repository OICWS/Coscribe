# A failed turn saved as a file, to start an evaluation task (shipped)

Why: the evaluation's tasks are guessed; the turns that went wrong in real use stay in
`turns.jsonl` on each machine. The last part of #867, under decision
[0051](../decisions/0051-a-failed-turn-leaves-the-machine-only-as-a-file-the-person-saves.md),
which decision 0045 asked for before anything of the record leaves the machine.

## Shipped
- `conversation/turn_export.py`: lists a conversation's turns that ended on an error, were stopped
  or had a tool fail (both `turns.jsonl` and the file put aside before it, newest first, at most
  20), and writes one as a file: the turn's numbers, field by field, without the conversation's
  id; the start of each tool error with the home folder as `~`; and the person's own words on
  what they asked and what went wrong, cut at 2,000 characters and redacted.
- Routes `GET /api/threads/{id}/failed-turns` and `POST /api/threads/{id}/failed-turns/export`
  (in `web/routes/threads.py`). Nothing is uploaded; the second answers with the file.
- "Export a failed turn…" in a conversation's menu opens `FailedTurnDialog`: pick the turn, write
  the two optional fields, look at the whole file, press Save the file. To keep `ThreadList.tsx`
  under the ratchet's limits, the menu's two exports moved next to the dialog and "Move to group"
  with its submenu moved to `BatchBar.tsx` beside "New group…"; neither changed.
- `python -m evals.agentic.candidate FILE` prints an `AgenticTask` to finish by hand.
- Tests: `tests/test_turn_export.py` (4), one in `tests/web/test_chat_trace.py`, one in
  `tests/test_evals_agentic.py`.

## Not verified
- The dialog in the desktop app on Windows: saving goes through the same `saveBlob` as "Export
  conversation", which was not tried here; and the home folder written as `~` on a real
  `C:\Users\<name>` path (the test uses a POSIX home).
- A real failed turn from a real model: the tests use recorded lines and a turn stopped at an
  approval.

## Follow-ups
- A task made from an exported file and added to `agentic/tasks.py`, once one comes in.
