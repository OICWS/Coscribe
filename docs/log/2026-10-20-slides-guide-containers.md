# The model's Slides guide teaches containers (shipped)

Why: the editor has containers (decision 0018) and a panel for them, but coscribe still wrote
every card as free-placed boxes, so the user's first edit to a card broke the layout around it.

## Shipped
- `engine/sections_guide/SKILL.md`: a "Containers" bullet in the section language (direction, gap,
  padding, align, justify, how children are sized, the card look, nesting) with when to use one
  and when to keep free placement, and a worked example of three cards in a row in "Layout".
- The guide is a skill loaded on demand, so the fixed tool list and the cached prompt are
  unchanged.
- `tests/test_sections_guide.py`: the guide has four examples now, and the test builds each one,
  so the container example never teaches a slide the compiler refuses.

## Not verified
- Whether a real model chooses containers for card layouts and writes them correctly; no model
  run was made. A small deck task on the evaluation would show it.

## Follow-ups
- Overwrite refusal for a hand-edited slide (plan.md).
