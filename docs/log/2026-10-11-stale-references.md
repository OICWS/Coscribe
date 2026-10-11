# A path named in a document or comment must exist, and 97 that did not are fixed (shipped)

Why: Step 3 of the structure period (record 0009). After `web/session.py` became `conversation/session.py`, 46 places in 30 files still sent a reader, or a session looking for what to read, to the old path; others named modules removed in the runtime migration (`runtime/runner.py`, `runtime/policies.py`, `tools/subagents.py`), the Tauri shell, or the old name of the desktop app. Nothing failed.

## Shipped
- `tests/test_doc_references.py` fails for a path that no tracked file ends with, in Markdown, the comments and docstrings of the Python source, and the comments of the TypeScript source. Not checked: the documents that record history (`docs/history`, `docs/log`, `docs/assessments`, the roadmap index, `PPTX_DESIGN.md`, the runtime README), vendored code, and tests. Shorthand lists (`cli.py/web/app.py`), tool lists (`Pandoc/Marp`) and `./` and `../` examples are skipped.
- `tests/doc_reference_allowlist.txt` holds the prefixes that are not ours: build outputs, files of the projects some code was ported from, Electron and library files. Adding to it loosens the test, so it is a `CODEOWNERS` path, with the test.
- The 97 references in 45 files are fixed: the moved session file renamed (46), the removed modules' mentions deleted with the comment sentence that only compared with them (the comment rule: history belongs in the commit message), the old desktop app name, the Tauri leftovers, the splash page named by its source, `context_usage.py`'s new place. Python files: only comments and docstrings changed (checked by comparing the syntax trees without docstrings: 22 files, none differ), and the tool-schema snapshot is unchanged.
- The ratchet baseline is lowered where the edits removed lines (`session.py` 3755 to 3743, `app.py` 1110 to 1102).

## Not verified
- The checker on Windows (it asks git for the file list, and compares with `/` paths).

## Follow-ups
- The history documents still name files as they were; the roadmap's step 7 gives each package a card that the same checker will cover.
