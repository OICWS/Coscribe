# Property test for the container layout (shipped)

Why: issue #464. `<x-stack>` containers (decision 0018) had example tests only; a layout
rule that fails on a combination nobody wrote down would show up as a card drawn outside its row.

## Shipped
- `office-agent/tests/test_deck_layout_property.py`: random `<x-stack>` trees (row or column,
  up to three levels, gap, padding, align, justify; children fixed, growing, shrinking or sized
  by their content) laid out through `parse_section`. Checks: children lie inside their container
  (unless content-sized and larger than the room), siblings follow each other a gap apart, growing
  children use all the free room in proportion to `flex-grow`, and two layouts of one tree give
  the same boxes.
- Each check was shown to fail by breaking `section_layout.py` locally (gap ignored when placing
  and when sharing room, grow split equally or short by 10%, padding ignored, shrink removed,
  cross-axis `end` wrong, a counter added to the offsets); the breaks are not committed.
- One engine quirk found, left as is (issue #464): a child with a large `flex-shrink` is cut to
  nothing and the room it could not give is not taken from the others, so the container
  overflows. The test skips the containment check for a container where a child was cut to nothing.

## Not verified
- `justify` is generated but not checked (not in the issue's list); removing the centring offset
  is not caught.

## Follow-ups
- The e2e specs for the Slides panels and containers are the second part of #464.
