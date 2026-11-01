# The workflow eval scores data tasks whose input drifts, with pass^k (#768)

Why: `evals/workflow/` only scored browser tasks. A saved task that runs code over a monthly
export fails differently: when the export drifts, a script seldom stops, and a wrong report
looks like a finished run.

## Shipped
- `evals/workflow/data_tasks.py`: two tasks with seeded data and a computed right answer:
  - a sales summary (paid orders of the month per region);
  - an invoice reconciliation against a bank export.
  - 7 drifts each, in how a file is written or in what it holds, plus a blank required value
    that must stop the run.
- `evals/workflow/data_run.py`:
  - Builds:
    - `drafted`: the app does the task once in a conversation, and the workflow drafted from it
      is saved.
    - `agent`: one bounded agent step with Python.
  - The judge reads the file written.
  - A failed run goes to its investigation.
  - `--repeat k` gives pass@1 and pass^k.
- `evals/workflow/app.py`: start a conversation and draft from it.
- `tests/test_evals_workflow_data.py`: the drifts, the right answers, the judge and the verdicts.

## Result (`--repeat 3`, `deepseek:deepseek-flash`, 84 runs)
| build | PASS | REPAIRED | SAFE_STOP | ASKED | FALSE_SUCCESS | GUESSED | NO_DRAFT | pass@1 | pass^3 |
|---|---|---|---|---|---|---|---|---|---|
| drafted | 10 | 16 | 4 | 0 | 4 | 1 | 7 | 33% | 21% |
| agent | 35 | 0 | 4 | 3 | 0 | 0 | 0 | 93% | 79% |

- **Drafted scripts fail loudly on most layout drift.** Renamed columns, `;` with a decimal
  comma, title lines and cp1252 all made the script fail, and the investigation repaired it in
  16 of 17 cases. They handled a new status and duplicate rows (3 of 3: the draft kept dedup
  and paid-only).
- **But they also fail silently, and that is the finding.**
  - All 3 reconciliation drafts matched payments with `INV-\d{4}-\d{4}`. When the bank's
    booking text changed, they reported paid invoices as open and said completed. Their checks
    covered references to unknown invoices but not credits that match no invoice.
  - One sales draft read a blank quantity as 0 (`int(... or "0")`) and wrote a report
    (`GUESSED`).
  - One repair wrote an incomplete report.
- **The agent step was never wrong**, but costs about 23 s and a model call per run (a script:
  3 s). Its 3 failures parked the run on a read-only tool it wasn't given (`search_files`). A
  bounded step parks for any undeclared call (decision 0028), even a read inside the workspace,
  so an unattended run waits on a person.
- `NO_DRAFT`: one draft timed out on the eval's 60 s client limit (now 600 s), and one came back
  400. The eval now records the reason.

## Not verified
- On Windows (Linux, scripts run as the user there).
- Two tasks; the sample is small, and the drafts vary run to run.
