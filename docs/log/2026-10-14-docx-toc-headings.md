# A Word table of contents lists the real headings in every viewer (shipped)

Why: `write_docx`'s `[TOC]` field showed only "Right-click and choose Update Field to generate the table
of contents." until Word recalculated it, so LibreOffice, PDF export, previews and the agent's own render
showed no contents list (#197; the judge's lowest Word score, 07-restructure, named it).

## Shipped
- `tools/office/docx/_xml.py`: `_add_toc` writes the field with an empty result; `_fill_toc` fills it with
  one paragraph per heading in the field's `\o "1-3"` range, styled `toc 1`/`toc 2`/`toc 3` (the
  template's own styles when it has them, else Word's built-in definitions, ids `TOC1`..), no page
  numbers. `updateFields` stays on, so Word rebuilds the result with page numbers on open. With no
  heading in range the result is Word's own "No table of contents entries found."
- `tools/office/docx/toolkit.py`: the result is written after every block of the content is laid out
  (just before validation and save), so headings after the `[TOC]` marker are listed too. With
  `track_changes` each entry paragraph is a tracked insertion like the rest of the content.
- The TOC entries repeat each heading's text, so the lookups by text skip a TOC field's result:
  `_locate_paragraph` (`replace_docx_text`, `insert_docx_text`, `delete_docx_text`) and the
  `after_text` anchor of `add_docx_chart`/`add_docx_image`. Without it, editing or anchoring on a
  heading failed as "found in 2 different paragraphs".
- A template style is reused when its name is `toc N`, or its id is `TOCN` with a name like `TOC N`;
  when `TOCN` is the id of an unrelated style, the added style gets a free id (`TOC1_2`), so no id
  is defined twice.
- The `write_docx` description says the field lists the headings in every viewer.
- `tests/test_docx_golden.py`: a shared part (styles, settings, ...) that a document changes is stored
  in its golden as a diff against `_shared.txt`, not as a full copy (the `toc` golden would otherwise
  carry 11.8k lines of `styles.xml` for two added styles). `golden/docx/toc.txt` now shows the
  headings inside the field result and the two TOC styles.
- Tests: the result lists headings written after the marker with their TOC styles; the level range is
  read from the field (`1-3` and `2-4`); the empty case; tracked entries; editing a heading and
  placing a picture after one in a document with a TOC; a template whose `TOC1` id belongs to another
  style, and one whose `TOC1` style is reused; a LibreOffice PDF of the document has the contents list
  where the field is.

## Not verified
- Word itself on Windows: that it replaces our result with its own (page numbers, hyperlinks for `\h`)
  on open and keeps the `toc N` styles. The field code and `updateFields` are unchanged from before.
- The TOC of a document edited later by the tracked-edit tools (`insert_docx_text` and the others) is
  not rewritten; Word refreshes it on open, other viewers show the headings as of `write_docx`.
