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
  replacement takes the format of the run the match starts in. A match never crosses a line
  break (`a:br`) or a field (`a:fld`, e.g. a slide number): rewriting across one would drop it.
- Deleting is explicit: `remove=true`. An empty `replace` without it is refused, so a forgotten
  argument cannot wipe a phrase from the whole deck, and `remove` with a `replace` is refused too.
  `replace` is one line; a newline in it is refused with a pointer to `content=`.
- `tools/_pptx_text.py` holds it; `tools/presentations.py` is 2 lines shorter. No new tool;
  `tests/tool_schemas.txt` changes for `edit_pptx_text`'s description.
- `tests/test_pptx_text_replace.py` (12 tests): a group member keeps its bold and colour, a
  phrase across runs, every slide with table cells, `remove`, a forgotten `replace` refused,
  `remove` with a `replace` refused, a newline in `replace` refused, no match across a line
  break, not found, `find` with `title` refused, `slide=0` without `find` refused.

## Not verified
- Windows.
- The model choosing `find` over listing shapes: measured with the edit tasks after PR 3.
