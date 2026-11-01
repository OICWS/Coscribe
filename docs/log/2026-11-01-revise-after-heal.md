# A heal no saved fix keeps is drafted as a revision (shipped)

Why: decision 0030 says a self-healing run proposes a revision. The fixes a heal named are saved
from the report (#762); a heal that changed more than a step's arguments (a new review page, a
new wording of the confirmation) left the saved steps describing the old page, so every run
healed it again.

## Shipped
- `workflows/heal_fixes.py`: `heals_to_revise(workflow, status, records)`, the heals of a
  finished run that no saved fix keeps.
- `runtime_lg/scheduled_tasks.py`: `start_investigation` opens on such a run with
  `build_revision_prompt`: each healed step, what failed and what the agent did instead, and the
  steps (revise, test, tell the person). The conversation is titled "Revise: <task>", and the
  app shows its opening message as "Revise the healed steps of ...".
- The investigate route accepts a finished run with heals to revise, and the scheduler starts
  the conversation by itself for a task set to look into runs.
- The run report: "Ask for a revision" under the heals no fix keeps. The run view's quiet link
  now reads "Open the conversation that looked into this run".
- `workflows/solidify.py`: a revision keeps every step the workflow it revises marks
  `irreversible`, and says so in its changes. Seen live: a model asked to let a test reach the
  end unmarked the submit step.
- Tests: the prompt (`tests/test_scheduled_runs_lg.py`), the route and the scheduler
  (`tests/web/test_heal_fixes_route.py`), the kept mark (`tests/test_workflow_solidify.py`).

## Live
- On the expenses test site (version 4: relabelled, a cookie dialog, a new required field and a
  review page), a run's heals of the submit and the reference were drafted into a revision that
  passed its test. That conversation, before the kept mark, had unmarked the submit step of a
  task saved before decision 0029, so its tests filed claims on the test site.

## Not verified
- On Windows.

## Follow-ups
- The workflow eval: save the fixes after a healed run, or the drafted revision, and run again,
  expecting a pass with no heal.
- A task saved before decision 0029 has no step marked; a revision marks the ones it sees, but
  the saved task stays unmarked until the person saves one.
