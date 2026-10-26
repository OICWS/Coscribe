# Task details > Outputs no longer lists working files that are gone (shipped)

Why: a run that checks its work leaves renders (`_qa/v3.pdf`, ...) and then removes them; the
Outputs list kept them as grey "No longer on disk" rows, a dozen of them above the real result.

## Shipped
- `conversation/activity.py`: an output that is gone from disk is left out unless the conversation
  read it before changing it (it may be the person's own file, and is then shown as gone). Before,
  only files the conversation had created were dropped; one made by a conversion tool counted as
  "edited" and stayed.
- A folder named `_qa` or `-qa` is the scratch folder `qa` (underscores and hyphens at the ends are
  ignored when matching the scratch names).
- Test: `tests/test_artifacts.py`.

## Not verified
- The panel with a real run's leftovers on Windows.
