# Deck engine, part 4: new decks are built from pages in the product (shipped)

Why: the measurement (`2026-10-14-deck-engine-measurement.md`) has the engine ahead on every
score for new decks at 0.94 times the cost; decision 0010 switches new decks when it wins
(issue #198, PR 4 of 4).

## Shipped
- `coordinator.py`: the paragraph the evaluation's `engine` route measured now follows the
  coordinator's instructions (`NEW_DECK_INSTRUCTIONS`, kept in
  `tools/office/pptx/engine/instructions.py`, so `coordinator.py` keeps its size). A new deck: load "PPTX Pages", write the pages, build with
  `build_pptx_from_pages`; a user's template or a deck the user brings stays on the template and
  edit_pptx_* tools. The sentence that loads "PPTX Slides" now names when: filling a template or
  writing with `write_pptx`. The system prompt grows by about 270 tokens (cached).
- "PPTX Pages" is a built-in skill (`builtin_skills/pptx-pages/`, moved from the engine's
  `guide/`); "PPTX Slides" stays, its description narrowed to templates and `write_pptx`.
- `evals/run.py`: `--route` is gone, since the engine route is now the product; a run measures
  the coordinator as it ships. The baseline of today's route stays in
  `2026-10-13-office-eval-part2.md`.
- Tests: the instructions name the built-in skill and the tool that exist; the built-in skill
  lists gain "PPTX Pages"; `tests/tool_schemas.txt`'s prompt line.

## Not verified
- Windows: the maintainer builds one new deck in the app before merging.
- In the measurement "PPTX Slides" was switched off; here it stays listed for template work. A
  new deck may still load it; the off-peak run after merging shows whether it does.

## Follow-ups
- Today's PowerPoint section of the instructions (write_pptx's layouts, choosing a template) now
  serves templates and edits only; trim it when `tools/presentations.py` is split.
- Edits of a deck built from pages go through its pages; the object tools' upgrade (decision
  0010) is next for decks the user brings.
