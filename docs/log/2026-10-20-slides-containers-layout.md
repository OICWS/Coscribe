# Containers in a section are laid out by the engine (0018 part 1)

Why: the auto layout the maintainer asked for (cards in a row that share the room, and share it
again when one goes) needs elements whose place comes from a parent (decision 0018). This is the
format and the layout; the editor does not use it yet.

## Shipped
- `<x-stack>` in a section (`engine/section_layout.py`): `data-layout="row|column"`, `gap`,
  `padding`, `align` (start, center, end, stretch), `justify` (start, center, end, between), and
  the look of a card (`background`, `border`, `border-radius`, `opacity`), which becomes a
  rectangle behind its children. A child has no `left` or `top`: along the container it takes
  `width` or `height`, or a share of the room (`flex-grow`, `flex-shrink`, `flex-basis`); across
  it, its own size or the container's room. Text in a column takes the height its words need
  (the engine's own text layout); a container without a height is as tall as its content.
  Containers nest, six deep at most.
- `parse_section` lays the containers out first, into the plain positioned elements everything
  else already reads, so the compiled deck, the app's drawing and the checks need no change.
- Tests: `tests/test_deck_layout.py` (sharing, deleting a card, fixed and growing children,
  hugging text, nesting, justify and align, shrinking, errors, a built deck, the editor's parts).

## Not verified
- Not opened in PowerPoint (the deck holds plain shapes).
- The editor cannot select a container or edit inside one yet: it numbers a section's elements by
  position among its children, and a section with a container has more elements once laid out.
  Nothing in the app creates a container, and the model's Slides guide does not mention them, so
  this only matters for a section written by hand until part 2.

## Follow-ups
- Parts 2 to 4 of 0018: the editor over the laid-out tree, drag in, out and reorder, the panels.
- The Slides guide for the model: containers for rows of cards.
