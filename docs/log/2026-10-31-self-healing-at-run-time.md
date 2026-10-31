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
- A heal names the saved arguments it changed (`changed`, e.g. `ref: textbox "Legal name"`;
  only literal ones, never a snapshot id). The run remembers each change by tool, argument and
  the value it replaced (`healed` in the graph state), and any later step whose saved argument
  had that value tries the new one first, with no agent: the step's next pass in a loop, and
  the same field's step for the next row in a workflow built row by row. A step that can't be
  undone isn't carried over: it heals with the person each time, and its agent is told what was
  done before.
- `report.py`: the report lists `healed`, a carried one marked as the same fix; `RunReportCard` shows "Healed while running".
- `AutonomySetting`: the self-healing description says what it now does.
- `tests/test_workflow_healing.py`: fixed doesn't heal; a heal inside consent; a heal of a step
  whose output is read; an irreversible heal waits for a yes; a heal that stops; a non-browser
  step isn't healed.

## Live (eval, fixed builds, `--autonomy self_healing --mark-submit --no-repair`, before carry-over)
- PASS 4, HEALED 1, SAFE_STOP 2, FAILED 7; no false success, nothing wrong filed.
- Relabels healed (the expenses run healed 18 steps). Every structural change (a new required
  field, a review page, a date format) was refused by the agent as more than the step did, and
  is left to the investigation.
- Each loop pass healed the same drift again, about 30 s and 150k tokens each, and judged it
  differently once: the suppliers relabel filed its first row and refused the renamed submit on
  the second. Carry-over is the answer.

## Not verified
- On Windows.

## Follow-ups
- After a heal, propose a revision of the saved step (decision 0030), so the next run doesn't
  heal the same change again.
- Heal steps other than browser ones (a connector whose API changed) once the eval covers them.
