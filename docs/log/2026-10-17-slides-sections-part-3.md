# Slides step 1, part 3: the Slides guide and an evaluation switch for decks as sections (shipped)

Why: the measurement of decision 0015 (#392, PR 3 of 4) needs the model to write decks as sections,
with the same design guidance as the SVG pages, while the product stays on the pages.

## Shipped
- `tools/office/pptx/engine/sections_guide/SKILL.md`, the "Slides" skill. It is not a built-in
  skill: only the evaluation installs it.
  - The section language, with one example of each kind of element.
  - The workflow, the design spec, layout and type copied from "PPTX Pages", with sizes scaled
    to the 1920-wide canvas. Visual styles, methods and icons are read from "PPTX Pages", so
    there is one copy of each.
  - After the maintainer compared one task's two decks and preferred the SVG one, the guide
    also asks for what that deck had and the sections' deck lacked:
    - a caption naming each table's and chart's unit, with short column headers;
    - a section label and a source and page footer on content slides;
    - blocks side by side sharing their top and bottom edges;
    - finding cards with an accent bar and a label.
- `sections_guide/instructions.md`: the coordinator's new-deck paragraph for sections. A deck on
  the user's own template stays on the SVG pages.
- `evals/run.py --language sections`: installs the guide in each task's skills folder and swaps the
  coordinator's new-deck paragraph for the run; `result.json` records the language.
- `tests/test_sections_guide.py`: the guide loads as a skill, every example in it builds without
  an error, and the runner swaps the paragraph and puts it back.
- Part 2's log records the Windows checks of build-ins and transitions.

## Checked
- One task (01-q3-review) on each route before the guide's additions: facts 19/19 on both,
  overlapping text 0 (sections) and 6 (pages), 97 s and 132 s, 0.022 dollars each.

## Follow-ups
- Part 4: all deck tasks on both routes, with the blind judge.
