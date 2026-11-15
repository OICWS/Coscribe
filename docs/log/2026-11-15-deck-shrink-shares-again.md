# A container's children shrink as CSS flexbox shares it (shipped)

Why: in an `<x-stack>` (decision 0018), a child whose `flex-shrink` asked for more room than it
had was stopped at nothing, and the room it could not give was taken from no one: its siblings
kept their size and the container overflowed (#846). Example: a column 400px tall holding a
container with no look (`height:100px;flex-shrink:50`) and a 500px shape; the shape came out
481.82px tall instead of 400px.

## Shipped
- `section_layout.py`: `_shrink` takes the missing room in proportion to `flex-shrink` times each
  child's size; a child that would go below nothing stops there and the rest is shared again among
  the others, until it fits or nothing can shrink any more.
- `tests/test_deck_layout.py`: the example above (the shape is now 400px), and a row where the
  lack is shared 1200 to 1600 by `flex-shrink` times width.
- `tests/test_deck_layout_property.py`: the `squeezed` exemption is gone, so the containment check
  covers these containers too.

## Not verified
- The property test's generator does not reach this case by itself (shrink factors up to 3,
  children capped at the room); widening it to look-less containers did not reach it either. The
  example tests are what fail on the old code.
- A leaf shrunk to nothing is still refused by the section reader ("width and height must be
  positive"), as before.
