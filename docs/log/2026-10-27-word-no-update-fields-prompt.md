# A written Word file with a table of contents opens without the update-fields prompt (shipped)

Why: a document coscribe wrote with a table of contents showed Word's "This document contains
fields that may refer to other files. Do you want to update the fields?" on every open.

## Shipped
- `_enable_update_fields` is gone: the `w:updateFields` setting in `settings.xml` is what made Word
  ask. The table of contents is still written with its entries (without page numbers); Word's own
  Update field adds the numbers.
- `test_write_docx_toc_marker_inserts_a_toc_field_and_no_update_prompt` and the `toc` golden now
  assert there is no `updateFields` setting.

## Not verified
- Opening the file in the real Word on Windows; the cause is read from the setting, not observed.

## Follow-ups
- None.
