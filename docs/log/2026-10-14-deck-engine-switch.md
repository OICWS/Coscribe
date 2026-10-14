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

## Checked (2026-10-14, at peak price)
Tasks 03, 04 and 05 on this change and #212's guide, `deepseek-flash` at effort low, 3 judge
rounds; before is the measurement in `2026-10-14-deck-engine-measurement.md`.

| Task | Facts | Numbers in no input | Design | Content | Coherence | Cost |
|---|---|---|---|---|---|---|
| 03-project-proposal | 18/18 (18/18) | 0 (5, one an invented date) | 4.27 (4.27) | 4.57 (4.60) | 4.50 (4.53) | 0.043 (0.027) |
| 04-product-launch | 12/12 (10/12) | 0 (0) | 3.63 (3.63) | 3.87 (4.17) | 3.87 (4.23) | 0.038 (0.047) |
| 05-long-report | 23/23 (22/23) | 1 (1) | 4.40 (4.23) | 4.30 (4.33) | 4.57 (4.47) | 0.050 (0.050) |

- All three faults the guide was changed for are gone: "399 元" and "50 元" are written as in the
  material, the survey keeps its 41%, no date the material lacks. 05's one flagged number is a
  share computed from the material.
- Scores are level within the judge's spread (04's content and coherence are 0.3 lower, about
  one spread). Cost 0.131 against 0.124 dollars; the run and its judge cost 0.148 at the page's
  off-peak prices, about 2.0 yuan at the doubled peak price it ran at.
- Each task loaded one skill and then wrote pages and built them; the run does not record the
  skill's name, so that it was "PPTX Pages" and not "PPTX Slides" is inferred from the workflow.

## Not verified
- Windows: the maintainer builds one new deck in the app before merging.
- Which skill a new deck loads, by name (above).

## Follow-ups
- Today's PowerPoint section of the instructions (write_pptx's layouts, choosing a template) now
  serves templates and edits only; trim it when `tools/presentations.py` is split.
- Edits of a deck built from pages go through its pages; the object tools' upgrade (decision
  0010) is next for decks the user brings.
