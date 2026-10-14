# Deck engine: ppt-master's native chart and table objects copied, unused yet (shipped)

Why: a page should be able to carry a chart or a table as data, so the deck gets a PowerPoint
chart (with its workbook, editable in PowerPoint) or a real table instead of drawn shapes.
ppt-master already converts such markers; this copies that code so the next PR can wire it in.
Decision 0010 covers vendoring from ppt-master.

## Shipped
- `tools/_native_svg/`: the import closure of upstream's `svg_to_pptx/native_objects/__init__.py`
  from the same commit as the emitter, 12 modules, about 10.7k lines (charts, the embedded
  workbook, tables, their markers and checks; `semantic_table.py` from the scripts directory).
- Changes to the copy: 4 more imports made package-relative (21 lines in all); nothing else.
  `NOTICE.md` lists the files and the changes.
- Nothing imports it yet; the package imports cleanly. The wiring, tests and a model run come
  with the next PR (native charts and tables on a page).

## Not verified
- Windows.
