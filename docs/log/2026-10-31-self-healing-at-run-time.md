# A failed browser step heals during the run at self-healing autonomy (partly shipped)

Why: in the workflow eval (#754) every fixed workflow that broke on a changed page waited for an
investigation and a saved revision, though most changes were a renamed field or a moved button.
Decision 0030 gave the `self_healing` level that job; until now it acted as `fixed`. The
maintainer chose that healing a step that can't be undone waits for a person, even with no one
watching.

## Shipped
- `workflows/healing.py`: when a browser tool step fails and the task's autonomy is
  `self_healing` or above, `stand_in` builds a bounded agent step from it:
  - the failed step's tool, rendered arguments and error;
  - the page tools only (no `browser_evaluate`, no uploads, no navigation unless the failed step
    navigated), on the sites the workflow already opens (`granted_by`);
  - the fields `did` (what it did instead) and `result` (what the tool would have returned, for
    a step a later one reads).
- `engine.py`: `_try` runs a step and hands a failure to healing, through the same `_agent` path
  (and pauses) as an agent step. A step marked `irreversible` heals with `confirm_changes`: every
  call that does more than read waits for a person. A heal that stops fails the step with both
  reasons. The step's record keeps `agent.healed = {error, did}`.
- `engine.py` gives up lines to stay under the size ratchet: `loop_labels.py` now holds the loop
  progress and graph size, and `connector_value.py` a connector result's value.
- `report.py`: the report lists `healed`; `RunReportCard` shows "Healed while running".
- `AutonomySetting`: the self-healing description says what it now does.
- `tests/test_workflow_healing.py`: fixed doesn't heal; a heal inside consent; a heal of a step
  whose output is read; an irreversible heal waits for a yes; a heal that stops; a non-browser
  step isn't healed.

## Not verified
- On Windows.

## Follow-ups
- After a heal, propose a revision of the saved step (decision 0030), so the next run doesn't
  heal the same change again.
- Heal steps other than browser ones (a connector whose API changed) once the eval covers them.
