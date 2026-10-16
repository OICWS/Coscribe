# Restructuring a Word document is one tool call, not a script (shipped)

Why: on Word task 07 (restructure a handbook) the model wrote 8-15 python-docx scripts in every
round, because the edit tools only change text inside paragraphs. In the product each script
needs Python on the user's machine and an approval.

## Shipped
- `edit_docx_structure` (#329), a deferred `WRITE_LOCAL` tool: a list of operations applied to an
  existing document, everything else left as it is:
  - `insert` markdown content (headings, lists, tables, `[TOC]`) `after` or `before` a paragraph,
    or `after_section` (after everything under a heading); it takes the document's own heading,
    list and table styles, and a new table's header follows the user's table style;
  - `move_section` and `delete_section` (a heading and everything under it);
  - a contents list filled from every heading once all operations ran, its title in "TOC
    Heading"; nothing saved if one operation fails; `output_path`; `track_changes` for inserts
    and deletes;
  - the result lists the edited file's headings, tables, pictures, header, footer and contents
    list.
- `write_docx` shares the block writer (goldens unchanged). Eval task 11 restructures a Chinese
  weekly report whose header, footer, picture and table style must survive.
- Measured, tasks 07 and 11, four rounds against main, every check passing:

  | | 07 main | 07 tool | 11 main | 11 tool |
  |---|---|---|---|---|
  | edits made by | scripts | one tool call | scripts | one tool call |
  | scripts | 8-15 | 1-3, read-only | 3-7 | 1-4, read-only |
  | seconds | 196 | 58-71 | 54-106 | 63-87 |
  | cost | 0.019 | 0.009-0.012 | 0.011-0.018 | 0.012-0.015 |

## Not verified
- The edited documents in Word on Windows.
- Judged scores on tasks 07 and 11: only the deterministic checks were compared.

## Follow-ups
- The model still checks its edit with 1-4 read-only scripts (paragraph styles, the contents
  field, table styles): a structure view in `read_docx`, its own PR since `read_docx` is bound
  to every session (decision 0001).
