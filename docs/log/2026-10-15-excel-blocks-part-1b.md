# Excel part 1b: the model writes workbooks in blocks (shipped)

Why: decision 0011, part 1b. The block and object operations from part 1a become the agent's
tools, and the measurement decides whether they replace the ten single-purpose writers.

## Shipped
- **`write_xlsx_cells` and `modify_xlsx`**: two deferred tools (`tools/office/xlsx/block_tools.py`).
  A block can take `from_csv`, a CSV file in the workspace, so a large table is never retyped.
- **`read_xlsx`** adds a `Layout:` section per sheet: the header's look, each column's number
  format and first formula, frozen panes, rules, validations, charts and widths. In round 1
  the model opened scripts to see these (six in task 05).
- **A write to a user's workbook** says its computed values are left out on purpose. In round 1
  the model resaved such a file with `recalc_xlsx`, undoing decision 0011's rule.
- **Every chart series gets a colour** from a palette. A line chart added after LibreOffice had
  resaved the workbook drew no line: a series left to the theme's colour is invisible there.
- **Data labels show the value only**: the flags left unset read as shown in LibreOffice, and
  series name, category and value piled up.
- **The Excel skill** is rewritten: plan, then write the workbook whole in two or three calls.
- **The system prompt's Excel paragraph** points to the two tools; it is 168 tokens shorter.

## Checked
Tasks 01–10, DeepSeek at effort low, judged blind against the earlier runs of the current
route and of the openpyxl-script route. Design out of 5, mean of three rounds; cost in yuan
for all ten tasks:

| | current route | script route | blocks, round 1 | blocks, round 2 |
|---|---|---|---|---|
| open tasks 02/04/09/10 | 2.88 | 3.73 | 3.88 | **4.18** |
| instruction tasks (6) | 3.89 | 3.81 | 4.26 | **4.34** |
| task 03 (adding to a user's sheet) | 4.00 | 3.03 | 4.40 | **4.27** |
| cost | 1.00 | 1.06 | 1.15 | **1.03** |
| minutes, all ten | 21.0 | 21.5 | 22.1 | **13.9** |

Every deterministic check passed in both rounds. Round 2 has the fixes above; in it tasks
01–08 took 27–61 s each (60–195 s before).

The weak spot is task 09, the sales report, at 3.03. The judge named overlapping data labels
(fixed after the run, not measured) and the model's own choices: a 17-page detail sheet and a
mislabelled column. Its run took 352 s, much of it in the model's task list and PDF previews.

## Not verified
- In Excel on Windows: the workbooks, the charts' colours, and a user's file opened without
  computed values.
- The data-label fix in a model run.

## Follow-ups
- Part 1c: remove the ten single-purpose writers, and add two tasks (a rich user workbook, a
  5,000-row table).
