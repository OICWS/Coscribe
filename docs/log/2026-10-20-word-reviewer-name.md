# A reviewer name in Settings for the Word panel's actions (shipped)

Why: third part of #473. The panel's replies and comments carried the computer's user name with no
way to change it.

## Shipped
- Settings > General > Review > "Reviewer name" (`COSCRIBE_REVIEWER_NAME` in `.env`, `Settings.reviewer_name`).
  It applies at once, with no restart. `POST /api/threads/{id}/docx-review` uses it as the author
  of the user's replies and comments; empty, it is still `getpass.getuser()`.
- coscribe's own review tools keep their `author` argument (default "Coscribe"); they do not read
  this setting.
- Tests: `tests/web/test_thread_activity.py` (a reply carries the name, a cleared name goes back to
  the user name; fails with the old line), `settings.spec.ts` (the field saves and clears).

## Not verified
- Real Word showing the name on a comment, and the Windows desktop app.

## Follow-ups
- The Slides panel's comments still use the computer's user name (`web/routes/slides.py`
  `_author`); they could read the same setting.
