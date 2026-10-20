# 0018: Sections may hold containers that lay out their children

Status: proposed (2026-10-20), for the maintainer to accept.

## Context
Every element of a section is placed by `left`, `top`, `width` and `height`. The maintainer wants
what the mockups show: three cards in a row, delete one and the others share the room, drag a
shape in or out and the cards adjust. That needs elements whose place comes from a parent, not
from their own coordinates. PowerPoint has no such thing, so what leaves the app is a snapshot.

## Decision
- **A container element, `<x-stack>`, holds elements and places them.** Its style has the box,
  `data-layout="row|column"`, `gap`, `padding`, `align`, and the look of a card (`background`,
  `border`, `border-radius`, `opacity`). A child of a container has no `left` or `top`; it takes
  `width`, `height` or a share of the room (`flex: grow shrink basis`). Containers nest.
- **The engine lays it out when the slide is drawn or built**, using the text layout it already
  has for a text box's height. The result is plain positioned shapes: the .pptx holds no
  containers and nothing reflows in PowerPoint. Free elements, old sections and decks opened
  from a .pptx are unchanged.
- **One layout, in the engine.** `slide_parts` returns every element's computed box, with its
  parent, so the editor holds no layout algorithm. A change (a child deleted, moved in, moved
  out, resized) is saved, and the boxes come back from the server; while dragging, the editor
  shows only where the element would land.
- **The model's Slides guide** gets containers for rows of cards; until it does, the model writes
  free elements as today.

## Consequences
- **Four parts, each its own pull request**: the format, the layout and its tests (no editor);
  the editor selecting and moving children by their computed boxes; drag in, out and reorder; the
  panels (a container's direction, gap, padding, alignment; a child's grow, shrink, basis).
- **The editor indexes elements by position among the section's children**; nested elements need
  an index over the whole tree (part 2).
- **Not decided here**: wrapping rows, grids, min and max sizes, a container inside a table.
