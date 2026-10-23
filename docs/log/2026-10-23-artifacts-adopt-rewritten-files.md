# A file the person brought, then replaced whole, becomes an artifact (shipped)

Why: a template deck the person attached was read and then rewritten in place by a script. The
Artifacts registry adopts only files the conversation created, so the finished deck never
appeared on the Artifacts page although it was what the conversation made.

## Shipped
- `conversation/activity.py`: each Outputs entry carries `rewritten`, true for a file created in
  the conversation and for one a script (`files_written`) or a `write_*` / `build_*` tool
  replaced whole, even when it existed before. `action` is unchanged, so the Outputs list reads
  as before.
- `conversation/artifacts.py`: `artifact_paths` adopts entries with `rewritten`. A file only
  read, or changed in place by an edit tool, is still not adopted.
- `tests/test_artifacts.py`: a brought deck rewritten by a script and a brought document
  replaced by `write_docx` are adopted; decks only read or edited in place are not.

## Not verified
- A real conversation on Windows. A script cannot tell a whole rewrite from a small change, so a
  workbook the person brought that a script merely tweaks is adopted too.
- Files in conversations that ended before this change are adopted the next time the page
  adopts that conversation, not at once.

## Follow-ups
- None.
