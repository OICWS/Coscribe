# A Doc's tables in the panel line up their numbers and bold a total row, as the Word file does (shipped)

Why: rendering the maintainer's sample Doc in the panel and as Word showed the Word file
right-aligning number columns and bolding a last "合计" row, while the panel did neither.

## Shipped
- `lib/docTableLook.ts`: a decoration plugin with the Word export's own rules
  (`table_layout._NUMBER_CELL_RE`, `_style._TOTAL_LABEL`). A column whose every filled body cell is
  a number is right-aligned with tabular figures; a last body row starting with a total word
  (合计, 总计, Total…) is bold under a rule.
- Unit test and an e2e case in `doc-editor.spec.ts`.

## Not verified
- The desktop app.
