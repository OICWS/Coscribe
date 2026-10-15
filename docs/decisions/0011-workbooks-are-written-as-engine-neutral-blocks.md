# 0011: Workbooks are written as engine-neutral blocks; Excel engines come in stages

Status: proposed (2026-10-15), for the maintainer to accept. Evidence:
`docs/assessments/2026-10-15-excel-quality.md`, design: `docs/assessments/2026-10-15-excel-design.md`.

## Context
A workbook written whole scored 4.1 of 5 on design against 2.8–3.2 for coscribe's
many-small-tools route, at the same cost. Claude for Excel and Microsoft's Agent Mode write a
block of cells (values or formulas with their styles) per call and return the computed results.
A script route needs a Python on the user's machine and an approval per run. Neither openpyxl
nor LibreOffice round-trips a user's workbook without loss (measured: sparklines, Excel 2010
extensions and cached values with openpyxl; a tab colour and rewritten styles with LibreOffice).

## Decision
- Workbooks are written through one engine-neutral operation list: blocks of cells with styles,
  and structure and object operations. Two tools (`write_xlsx_cells`, `modify_xlsx`) replace
  the ten single-purpose writers once they meet the evaluation's gate. Every write returns its
  computed results and the checker's findings by cell.
- Stage 1 executes them with openpyxl and LibreOffice, so no Excel is needed. A user's workbook
  is never saved with a loss: a write that would drop a feature goes to a copy and names what
  it lacks, and the original is not resaved by LibreOffice.
- Real Excel through COM (stage 2) and an Office.js add-in (stage 3) are later executors of the
  same operations. COM comes first. The add-in waits for a spike on deployment and on reaching
  the local server.

## Consequences
- The tool list changes once (0001): the schema snapshot and the coordinator text change in a
  reviewed PR, and the new schemas must be smaller than the ones they replace.
- `run_python_script` stays for analysis; results enter a workbook as formulas through the
  tools.
- A workbook preview in the app uses LibreOffice's HTML export of the recalculated copy.
