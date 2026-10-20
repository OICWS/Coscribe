# Slides: a line is dragged by its ends (shipped)

Why: the maintainer's testing: a line could only be moved and stretched as a box, so it could not
be turned to another direction.

## Shipped
- A selected line shows a handle on each end instead of a frame with eight handles; dragging an
  end moves it, the other end stays, and the line turns when the ends cross.
- Section language: a line runs from the box's top-left to its bottom-right corner, or from its
  bottom-left to its top-right with `data-direction="up"` (`x-shape` only on a line). A line may
  have zero height or width, so a horizontal or a vertical one is exact. The Slides guide names
  both.
- The converter takes the SVG page's lines going up to the right as such (they stayed drawings),
  and `tests/test_svg_to_section.py` compares the line's drawn path with the page's.
- The editor draws a line itself, always, so it follows the pointer; the server's picture of a
  box could not turn.
- Tests: `tests/test_deck_lines.py`, `lib/slideLine.test.ts`, and the "line" case of
  `slides-panels.spec.ts` (drag the right end down, then the left end past it).

- Reading a slide for the editor is tried once more when the request never reached the server.
  The Windows e2e run failed the table case once because Chromium reported
  `net::ERR_NO_BUFFER_SPACE` on that read, which left the editor without its slide.

## Not verified
- Not opened in PowerPoint. The e2e case passes against a live server with the stub model.

## Follow-ups
- A line inside a container is placed by the container and has no end handles.
