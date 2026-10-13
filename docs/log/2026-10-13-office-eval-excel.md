# Office evaluation, part 2, Excel: eight tasks, workbook checks, and the baseline of today's route (shipped)

Why: part 1 (#155, #171) measures decks. Decision 0010 puts Excel second, so its baseline has to exist before
any Excel engine work starts (#164, PR 1 of 2; Word is PR 2).

## Shipped
- `--kind xlsx` on `evals.run`, `evals.judge` and `evals.compare` (the part-1 runner, judge and comparison, not
  a copy): the task folder, the file the agent made, the checks, the summary columns, the judge's rubric and the
  comparison's check columns are chosen by kind. `pptx` is the default and its output is unchanged. The shared
  text checks moved to `evals/text_checks.py` and the LibreOffice render to `evals/render.py`.
- `evals/xlsx/tasks/`: 8 tasks (messy CSV to a clean table, monthly summary by formula, lookup across two sheets,
  line chart, edit of a formatted workbook, profit model, Chinese headers with 元 / 万 formats, dropdown list).
  `xlsx/make_inputs.py` rebuilds their inputs.
- `evals/xlsx_checks.py`, plain Python: opens; recalculated through the helper `recalc_xlsx` uses (formula count,
  error cells); facts; numbers in no input; cells by value (number within a tolerance, text exactly, real
  dates); formula-not-constant and input-not-formula ranges; number formats; bold; nothing outside the used
  range; untouched cells keep their styles and the original's conditional formats and validations survive;
  charts (kind, title, axis titles, points); dropdown lists; a probe that changes inputs on a copy and
  recalculates it; and legibility (cells printed as `###`, text cut off by a taken neighbour).
- `tests/test_evals_xlsx.py` (87 tests) and `tests/xlsx_reference.py`: a good answer to every task, which a test
  recalculates through LibreOffice and requires to pass every check (skips without LibreOffice), so a task that
  cannot be solved or an `expect.json` that rejects a right answer fails the run. A workbook of pasted numbers
  passes the cell values and fails the formula and probe checks.
- Harness fix: a relative `--out` reached the agent's tools as a relative state folder, so `run_python_script`
  and `convert_office_file` failed inside every run; the folder is resolved first.

## The baseline (route `current`, `deepseek-flash`, effort low, 3 judge rounds, off-peak, run twice)

| Task | Design | Content | Coherence | Cells right | Formulas | Probe | Styles kept | Legible (### / cut-off) | Numbers in no input | Tool calls | Seconds | Cost |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 01-clean-csv | 4.33 ±0.24 | 4.67 ±0.47 | 4.67 ±0.47 | 41/41 | - | - | - | yes (0 / 0) | 3 | 7 | 47 | 0.0092 |
| 02-monthly-summary | 4.00 ±0.00 | 4.83 ±0.24 | 4.23 ±0.21 | 25/25 | yes | yes | yes | NO (0 / 1) | 12 | 16 | 73 | 0.0129 |
| 03-lookup-two-sheets | 3.67 ±0.24 | 4.50 ±0.00 | 4.27 ±0.21 | 29/29 | yes | yes | yes | NO (0 / 2) | 6 | 10 | 57 | 0.0099 |
| 04-line-chart | 3.17 ±0.24 | 4.00 ±0.41 | 3.83 ±0.47 | 26/26 | - | - | - | yes (0 / 0) | 0 | 10 | 51 | 0.0097 |
| 05-edit-budget | 4.67 ±0.24 | 4.67 ±0.24 | 4.67 ±0.24 | 11/11 | yes | - | yes | yes (0 / 0) | 8 | 6 | 59 | 0.0102 |
| 06-budget-model | 3.90 ±0.29 | 4.50 ±0.41 | 4.33 ±0.24 | 15/15 | yes | yes | - | yes (0 / 0) | 5 | 11 | 26 | 0.0086 |
| 07-chinese-formats | 4.33 ±0.24 | 4.70 ±0.22 | 4.50 ±0.00 | 28/28 | yes | - | - | yes (0 / 0) | 12 | 19 | 84 | 0.0127 |
| 08-validation-list | 3.60 ±0.43 | 4.33 ±0.24 | 3.90 ±0.65 | 12/12 | yes | yes | yes | NO (0 / 1) | 0 | 6 | 43 | 0.0087 |
| **mean / total** | 3.96 | 4.53 | 4.30 | | | | | | | 85 | 439 | 0.0818 |

The second run, from the same code:

| Task | Design | Content | Coherence | Cells right | Formulas | Probe | Styles kept | Legible (### / cut-off) | Numbers in no input | Tool calls | Seconds | Cost |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 01-clean-csv | 4.27 ±0.21 | 4.20 ±0.22 | 4.50 ±0.00 | 41/41 | - | - | - | yes (0 / 0) | 3 | 7 | 67 | 0.0102 |
| 02-monthly-summary | 4.33 ±0.24 | 5.00 ±0.00 | 4.33 ±0.24 | 25/25 | yes | yes | yes | NO (0 / 1) | 12 | 11 | 58 | 0.0112 |
| 03-lookup-two-sheets | 3.83 ±0.24 | 4.50 ±0.00 | 4.50 ±0.00 | 29/29 | yes | yes | yes | NO (0 / 2) | 6 | 8 | 69 | 0.0116 |
| 04-line-chart | 3.33 ±0.24 | 4.33 ±0.24 | 3.83 ±0.24 | 26/26 | - | - | - | yes (0 / 0) | 0 | 11 | 111 | 0.0142 |
| 05-edit-budget | 4.70 ±0.14 | 4.97 ±0.05 | 4.93 ±0.09 | 11/11 | yes | - | yes | yes (0 / 0) | 8 | 12 | 120 | 0.0157 |
| 06-budget-model | 2.50 ±0.00 | 3.33 ±0.24 | 3.83 ±0.24 | 15/15 | yes | yes | - | NO (0 / 8) | 5 | 13 | 57 | 0.0095 |
| 07-chinese-formats | 1.83 ±0.24 | 3.00 ±0.00 | 3.67 ±0.24 | 28/28 | yes | - | - | NO (8 / 2) | 12 | 11 | 21 | 0.0084 |
| 08-validation-list | 3.77 ±0.21 | 4.33 ±0.24 | 3.83 ±0.24 | 12/12 | yes | yes | yes | NO (0 / 1) | 0 | 8 | 40 | 0.0086 |
| **mean / total** | 3.57 | 4.21 | 4.18 | | | | | | | 81 | 543 | 0.0894 |

Cost is in the units of DeepSeek's pricing page (the same as the PowerPoint baseline). Seconds are the sum over
tasks; three ran at a time. Two runs of one route differ by up to 2.4 points of design on a single task
(07-chinese-formats 4.33 and 1.83), so only a gap larger than that on one task, or the means over eight, is a finding.

What the baseline shows:
- Every value, formula, format, style and dropdown check passes in both runs, apart from the `###` of the second
  run, so the agent does what is asked. What it does not do is size columns: 4 of 8 workbooks (run 1) and 6 of 8
  (run 2) have cut-off text and one has `###` cells, which is where the judge's design score is lowest (#193).
- Both runs of 04-line-chart score lowest after that on design (3.17 and 3.33): the judge names a chart that
  runs past the page and crowded month labels.
- The agent gets the lookup, the SUMIFS summary and the profit model as real formulas (probe passes in all
  runs), and keeps the formats of an edited workbook.

## Not verified
- Windows (the checks and the render were run on Linux with LibreOffice).
- The judge shares a vendor with the model that made the workbooks; no Gemini round was run.
- The printed pages show values only, so the judge cannot tell a formula from a number; the probe and the
  formula check do that.
- Task 05's second run is recorded with status `error` and an empty message; its workbook was produced and
  checked like the others.

## Follow-ups
- Word tasks and checks (PR 2 of #164).
- #193: column widths in workbooks the agent writes.
