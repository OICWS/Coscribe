# `list_pptx_shapes` no longer crashes on group shapes (shipped)

Why: #135. `_describe_shape` read `shape.click_action` on every shape, and
python-pptx's `GroupShape.click_action` raises `TypeError`, so a slide holding
a `<p:grpSp>` could not be listed at all.

## Shipped
- `_describe_shape` (`tools/presentations.py`) skips the click action for a
  group: its `hyperlink` is `None`.
- A group is listed as one shape; its children are not listed. Addressing
  shapes inside groups is the larger design change the issue leaves out.
- `test_list_pptx_shapes_lists_a_group_shape_without_crashing` builds a deck
  with `shapes.add_group_shape()`. It fails on main with the `TypeError` and
  passes with the change.

## Not verified
- Decks produced by an SVG-to-DrawingML converter (only a python-pptx group).

## Follow-ups
- Listing and editing group children comes with the office-route work.
