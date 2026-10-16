# read_docx shows a document's structure, so checking an edit needs no script (shipped)

Why: with `edit_docx_structure` the edits on Word tasks 07 and 11 were one call, but the model still
ran 1-4 read-only python-docx scripts per task to see paragraph styles, table styles, pictures, the
contents field and the header and footer, which the markdown view leaves out.

## Shipped
- `read_docx(path, view="structure")` (#331): one line per top-level block (a paragraph's style and
  the start of its text, a picture's size, tracked changes, a section break; a table's size, style
  and first row; a contents list and its entry count), then each section's page, header and
  footer. `view="text"` is unchanged.
- `read_docx` is bound to every session, so its schema changed once (decision 0001): `view?:string`,
  description 248 to 546 characters.
- Measured, tasks 07 and 11, two rounds, every check passing, no script in any run:

  | | 07 (#330) | 07 | 11 (#330) | 11 |
  |---|---|---|---|---|
  | `run_python_script` | 1-3 | 0 | 1-4 | 0 |
  | seconds | 58-71 | 18-25 | 63-87 | 46-47 |
  | calls | 6-9 | 5-6 | 10-21 | 9-15 |
  | cost | 0.009-0.012 | 0.008-0.009 | 0.012-0.015 | 0.012 |

## Not verified
- Whether the model called the structure view in these runs: the audit log records only tools
  that write.
