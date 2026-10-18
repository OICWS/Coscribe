# A property test for arranging slides and undo (shipped)

Why: batch 10 item 9 (#425). The arrange functions and undo were tested by hand-picked cases only.

## Shipped
- `tests/test_deck_arrange_properties.py`: Hypothesis draws up to ten steps (new, copy, move,
  delete, save, comment) against the two-page deck of `test_deck_engine.py` and runs them through
  `insert_slide`, `duplicate_slide`, `move_slide`, `delete_slide`, `save_slide`, `add_comment` and
  `step_history`. After every step: the pages are numbered `01..N` in order, `read_deck` lists N
  slides with `changed` false and the .pptx holds N, no `.arranging-*` file is left, every comment
  points at an existing slide. Then it undoes every step and the pages equal the first ones byte
  for byte. Twenty examples, about 10 seconds.
- Checked by breaking: with `move_comments` doing nothing it fails (a comment names a slide that
  is gone); with `_write` renaming a page straight to its target instead of through the temporary
  name it fails (`FileNotFoundError` on `.arranging-1.svg`).

## Not verified
- Windows: it runs in the Windows job like every test; not run on a Windows machine here.
