# `tests/web/test_chat.py` and `test_threads.py` split by topic (shipped)

Why: #348 item 5. The two files were 2,531 and 2,216 lines; a change to one route group had to load all of it.

## Shipped
- `test_chat.py` (2,531 lines) became ten files by topic: the turn, questions, stop, modes, history,
  hooks, policy, events, task drafts, messaging. `test_threads.py` (2,216 lines) became seven: threads,
  approval preview, history, uploads, folders, activity, thread files. Test bodies are unchanged.
- `_libreoffice_actually_works` and `_write_test_deck`, used by two of the new files, moved to `tests/web/helpers.py`.
- The conversation card's Tests line and the test layout paragraph in `office-agent/CLAUDE.md` name the new files.

## Not verified
- 152 tests collect before and after with identical names; the 17 files pass locally (152 passed).
  CI's full run is the check for the rest of the suite.
