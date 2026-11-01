# A run's heals are offered as a fix to save into the task (partly shipped)

Why: a heal (decision 0030) fixes a step for its run only, so every later run healed the same
renamed field again, at the cost of an agent each time. Decision 0030 says a revision is proposed
after a heal.

## Shipped
- `workflows/healing.py`: a heal's record keeps, next to the saved arguments it changed
  (`args`), the values they replaced (`was`).
- `workflows/heal_revision.py`: `heal_fixes(workflow, healed)` turns a run's heals into a revision:
  each named change replaces the saved argument, but only while the task still holds the value
  the heal replaced, so a task edited since the run is never overwritten. A heal reused on a
  later item counts once. A heal that named no argument, or a step healed to different values on
  different items, is listed as `left`.
- The run report route adds `fixes` (`fixes`, `workflow`, `left`).
- `HealFixesSection` in the run report: "Keep these fixes so the next run doesn't need healing",
  the changes (argument, old value, new value), and "Save into the task", which saves the
  revision through the task's PATCH. The steps whose heals can't be saved this way are named.
- Tests: `tests/test_workflow_heal_fixes.py` (5), `tests/web/test_heal_fixes_route.py` (offered,
  saved, then no longer offered).

## Not verified
- On Windows.
- With a heal from a real run in the app: checked in Chromium on a run whose step record was
  given a heal by hand (the report, the button, the saved task).

## Follow-ups
- A heal that changed more than an argument (`left`): draft the revision in a conversation, as
  the investigation does for a failed run.
- The workflow eval: save the fixes after a healed run and run again, expecting a pass with no
  heal.
