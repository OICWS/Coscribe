# Container and child panels, containers to insert (0018 part 4)

Why: the last part of 0018: a container's layout and what it asks of the elements it holds can be
set in the panel, and a container can be made in the app at all.

## Shipped
- A container selected shows Layout (direction, gap, padding, align, justify) and its card's
  Appearance (background, opacity, radius, border), `SlideContainerProperties.tsx`. A change of
  direction fits what it holds to it (`setDirection`).
- An element placed by a container shows "Size in the container" under its own panel: grow,
  shrink, basis, width and height (0 is automatic).
- Bring forward and Send backward work among an element's siblings: on the slide the stacking
  order, in a container the place in the layout (`siblingOf`); the lock for slides with containers
  is gone.
- Insert, Shapes menu: Row container and Column container (a light card with two texts).
- The engine: what is sized by its content (text, a container with no height) does not shrink
  below it when the room is short; it overflows, as in CSS, instead of squeezing its text.
- Tests: the container inserts are in the DOM test whose sources the server judges
  (`sectionDom.test.ts`, `tests/test_slide_sources.py`), `slideStacks.test.ts`,
  `tests/test_deck_layout.py`.

## Checked
- In Chromium against a live server, a row of three cards: a gap of 100 px narrowed the cards
  (493 px each); the direction switched to column and back; grow 2 on a card made it twice as wide
  as the others (740, 370, 370); a Row container inserted; Bring forward on a heading inside a card
  moved it after the paragraph.

## Not verified
- Not opened in PowerPoint. Aspect (the mockup's) and wrapping are not offered.

## Follow-ups
- The model's Slides guide: containers for rows of cards (0018), with a measurement.
- A new-slide layout built from containers.
