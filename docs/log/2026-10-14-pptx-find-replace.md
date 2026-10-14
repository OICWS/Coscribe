# PowerPoint part 2, PR 2: find and replace a phrase in any shape, keeping its format (shipped)

Why: the most common change to a finished deck is a word or a number ("399 元" to "349 元").
Before, the model listed a slide's shapes, found the one holding the phrase and rewrote it, slide
by slide, and could not reach text inside a group or a table at all through `edit_pptx_text`.
Each of those steps is a model call; a find and replace is one.

## Shipped
- `edit_pptx_text(find=..., replace=...)`: every occurrence of `find` on one slide, or on every
  slide with `slide=0`, in placeholders, text boxes, group members (through PR 1's paths) and
  table cells. The result lists where it was replaced (slide, shape path, name, count). A phrase
  that is not there says to read the slide with `read_pptx` (spaces, full-width characters,
  separators). `find` is used instead of `title`/`content`, never with them.
- Format: a paragraph's runs each keep their font, size and colour. The match is found in the
  paragraph's whole text, so a phrase split across runs ("399" bold, " 元" plain) is found; its
  replacement takes the format of the run the match starts in.
- `tools/_pptx_text.py` holds it; `tools/presentations.py` is 2 lines shorter. No new tool;
  `tests/tool_schemas.txt` changes for `edit_pptx_text`'s description.
- `tests/test_pptx_text_replace.py` (8 tests, 6 fail without the change): a group member keeps
  its bold and colour, a phrase across runs, every slide with table cells, removal, not found,
  `find` with `title` refused, `slide=0` without `find` refused.

## Not verified
- Windows; a phrase broken by a line break inside a paragraph is not found (the break is not a
  run).
- The model choosing `find` over listing shapes: measured with the edit tasks after PR 3.
