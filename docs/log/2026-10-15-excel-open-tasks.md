# Excel evaluation: two open tasks and the research on quality (shipped)

Why: the eight Excel tasks name every cell, so the baseline passed them all and could not show
where a workbook loses quality. The research that uses them is
`docs/assessments/2026-10-15-excel-quality.md`.

## Shipped
- Tasks `09-sales-report` (a 480-line ledger made by `make_inputs.py`, a report for the boss)
  and `10-store-forecast` (three years from seven assumptions), whose layout is the model's
  choice, with reference solutions.
- Checks for such tasks:
  - `figures`: numbers in any cell, in ones, thousands or 万;
  - `formulas_min`;
  - `input_probe`: an assumption found by its value, changed on a copy, and the recalculated
    results compared.

  They appear in the run's summary table.
- The number-format check reads `yyyy\-mm\-dd` as `yyyy-mm-dd`: a backslash only escapes a
  literal.

## Not verified
- The tasks' workbooks in Excel on Windows (LibreOffice renders them for the judge).

## Follow-ups
- `build_xlsx`, a whole-workbook spec compiled in one call (in `docs/plan.md`).
- The recorder's `tool_seconds` pairs calls by name, and some tools get wrong times.
