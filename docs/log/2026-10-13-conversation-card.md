# `conversation` has a package card (shipped)

Why: #166, structure-period step 7. Last of the three package cards (`runtime` #183, `code_runtime` #189).

## Shipped
- `conversation/AGENTS.md` (+ `CLAUDE.md`); `tests/test_module_cards.py` covers it. It describes the package as it is while `ChatSessionLG` is still being split (#162), and says so, so the card is easy to update as pieces move.
- `conversation/__init__.py` exports `ChatSessionLG`, `ThreadMetaStore`, `OPENABLE_EXTENSIONS`, `open_in_os`; callers in `cli`, `web` and the tests import them from the package. Import lines only. Tests that need private helpers of `session.py` keep importing it.

## Not verified
- A real conversation on Windows with a real model (listed on the card under "Verify by hand").

## Follow-ups
- Update the card when the `ChatSessionLG` parts (#162) land; `docs/plan.md` is updated once at the end of the batch.
