# A workflow has one autonomy setting, and a run has a report (in review)

Why: a person thinks about a task's autonomy, not each step's: a finance task stays fixed, a
report may adapt. A run that adapts is only trusted when its result says what it did. Agreed
in #754; decision 0030.

## Shipped
- **`workflow_spec`**: `Workflow.autonomy` (`fixed`, `self_healing`, `proactive`,
  `autonomous`) as a ceiling.
  - Parsing refuses a step above it and names the step.
  - Without the setting, `effective_autonomy()` is the lowest level the steps need.
  - The helpers are `step_autonomy`, `needed_autonomy` and `steps_above`.
- **`workflows/report.py`**: `run_report`, read from a run's step records. It gives:
  - each loop's items done of total;
  - the steps not done and why;
  - what an agent decided itself (`agent.assumed`, #756);
  - the steps marked irreversible that ran (#758);
  - agent tool calls, tokens and time.
- **Route**: `GET /api/scheduled-tasks/{id}/runs/{run}/report`.
- **Frontend**:
  - `AutonomySetting` in the workflow editor: "Match the steps" or one of the four levels. The
    server's refusal is shown under it.
  - `RunReportCard` on a finished run.

## Not verified
- On Windows.
- `self_healing` acts as `fixed` until run-time healing ships; its description says so.

## Follow-ups
- Run-time self-healing, which pauses before a healed irreversible step (decision 0030). Its
  hook goes in a module of its own, since `engine.py` is over the size ratchet.
