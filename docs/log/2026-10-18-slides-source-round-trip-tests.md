# Unit tests for the Slides editor's source round trip (shipped)

Why: batch 10 item 10 (#425). `writeTextBack`, `drawSection`, `retag`, `newElement`, `setNotes` and
`slideLayouts` use the DOM, which vitest had no environment for, so none of them was tested.

## Shipped
- `frontend/src/components/slides/sectionDom.test.ts` runs in jsdom, set for that file only
  (`// @vitest-environment jsdom`); the other test files keep the faster `node` environment.
  `jsdom` 26.1.0 (MIT) is a new dev dependency: 27 and later need Node 22.12 or newer and CI
  runs Node 20. It checks, per function: the ten layouts are readable sections and each draws;
  every insert (text, table, six shapes, picture) adds an element with a whole-px box; text typed in
  the browser (`div`, `font`, bold) comes back as the section language's tags; a list keeps one
  `li` per line; a paragraph becomes a list and back; notes are added, changed and removed.
- It writes every source it produced to a file when `SLIDE_SOURCES_OUT` is set, and
  `tests/test_slide_sources.py` runs it that way and has the server judge them: each is accepted by
  `parse_section` and the whole set compiles with no errors. The test is skipped without node and
  the frontend's `node_modules`.
- Checked by breaking: a layout with an `<h5>` fails the parser test, an insert with an unknown
  `data-shape` fails the compile test, and `writeTextBack` not turning a `div` into a line break
  fails the vitest test.

## Not verified
- jsdom is not a browser: how a real browser's `contenteditable` marks up typed text is shown by the
  Playwright spec of item 8, not here.
