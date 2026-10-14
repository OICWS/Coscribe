# PowerPoint part 2, PR 3: ids name shapes for the edit tools, and an edit task on a built deck (shipped)

Why: PR 1 and 2 let the edit tools reach shapes inside groups and replace text anywhere; the
model needs to know that a page's ids become the names those tools take, and the evaluation
needs a task that can only be done that way.

## Shipped
- The compiler already names a shape after its element's `id`, a group's or a single
  element's. `build_pptx_from_pages`' description now says any id becomes the shape's name the
  edit tools take, and asks for one on a figure the user may change (`<text id="price">`).
- "PPTX Pages": when the build refuses because the .pptx changed after it was built, a word or
  a number is changed with `edit_pptx_text`'s `find` on every slide at once, a shape through
  `list_pptx_shapes` and its name or path.
- `tests/test_deck_engine_tool.py`: a page's `<text id="price">` is reached by name by
  `edit_pptx_shape`. It pins behaviour that already worked, so it passes without this change.
- Evaluation task `11-edit-built-deck`: a three-slide deck compiled from pages (the .pptx only, as
  a colleague hands it on, benefits as groups); change the price everywhere, replace one
  benefit's name and detail inside its group, recolour the three number circles. Its input is
  built by `evals/pptx/make_inputs.py`.

## Checked (2026-10-14, off-peak)
Tasks 07 and 11 with PR 1 to 3, `deepseek-flash` at effort low, 3 judge rounds.

| Task | Facts | Design | Content | Coherence | Tool calls | Cost |
|---|---|---|---|---|---|---|
| 07-edit-deck | 5/5 | 3.17 | 4.47 | 3.77 | 40 | 0.026 |
| 11-edit-built-deck | 6/6 | 3.60 | 4.57 | 3.90 | 14 | 0.012 |

- Task 11 was done the way PR 1 and 2 meant: `edit_pptx_text(slide=0, find="399",
  replace="349")` once for the price on two slides, `find` for the benefit's name and detail
  inside its group, `edit_pptx_shape` on paths `1/0`, `2/0`, `3/0` for the three circles; 14
  tool calls and 0.012 dollars (about 0.08 yuan). Every other shape kept its text and colour.
- 07 (the user's own deck, no groups) scores as before (3.20 / 4.33 / 3.90 in the measurement).
- With the judge the two cost 0.046 dollars, about 0.3 yuan.

## Not verified
- Windows.
