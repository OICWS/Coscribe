# Drag elements into, out of and within containers (0018 part 3)

Why: what the maintainer's mockups show (drag a card, a shape or a text in or out of a row of
cards and the cards share the room again) needs the editor to move elements between containers.

## Shipped
- Dragging an element over a slide with containers shows where it would land: the innermost
  container under the pointer outlined, and a line where the element would go among what it holds
  (`lib/slideStacks.ts` `dropTarget`, `DropMark` in `SlideEditor.tsx`, `useStackDrop.ts`).
- On the drop the element is moved there (`moveInto`): a free text takes the container's room
  (its position and, in a column, its width and height go; in a row it keeps its width), a child
  moved to a container of the other direction loses the sizes of the old one. Dropped on empty
  slide, a child leaves its container and takes the box it was dragged to (`moveOut`). The slide
  is read from the server after, so the cards share the room again; the moved element stays
  selected. A container cannot be dropped into itself or what it holds.
- What a container places can be moved this way but not resized by hand yet (part 4).
- Tests: `lib/slideStacks.test.ts` (where a point drops, the moves, in a DOM).

## Checked
- In Chromium against a live server, a row of three cards: a card dragged between two others
  (order changed in the saved section); a heading dragged from one card into another and then out
  onto the slide (each saved as expected).

## Not verified
- Not opened in PowerPoint. Not tried with a touch screen. A text dragged into a row takes a share
  of the room (`flex-grow:1`) when it has no width of its own.

## Follow-ups
- Part 4 of 0018: a container's panel (direction, gap, padding, align, justify) and a child's
  sizing (grow, shrink, basis), and Bring forward and Send backward in a slide with containers.
