# SpreadsheetBench dev baseline, and two runner fixes (shipped)

Why: the first pass over SpreadsheetBench's dev tasks gave 0 on every task, and the run stopped
partway.

## Shipped
- `evals/external.py`: five of the dataset's tasks name their files `initial.xlsx` and
  `golden.xlsx` rather than `1_<id>_init.xlsx`; the runner now finds them instead of crashing
  the whole run.
- A grader that cannot run (the default Python lacked numpy, which the benchmark's
  `compare_workbooks` imports) leaves the task ungraded instead of scoring it 0, so a broken setup
  can no longer pass for a bad score. Pass `--grader-python` with a Python that has numpy and
  openpyxl.
- Baseline: 34 of the first 40 dev tasks pass (85%) on `deepseek-flash`, $0.019 a task. The six
  failures:
  - 43436 and 45738: wrong logic in the formulas.
  - 51289: answers in the wrong cells.
  - 54667: a blank where the expected answer is a zero time.
  - 51680: header text trimmed where the expected answer keeps a header's trailing space.
  - 43657: counting green cells, which no formula sees, answered with zeros.

## Not verified
- The other 60 dev tasks and the held-out tasks were not run.

## Follow-ups
- No one cause covers the failures. The next lever is a check of a formula's results against
  one row worked by hand before finishing (43436, 45738).
