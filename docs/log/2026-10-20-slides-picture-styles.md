# A picture takes rounded corners, a border and opacity (shipped)

Why: the picture panel had only the file, fit and alt text, while shapes had a look. The section
language gave a picture no way to hold one, and a look the deck cannot carry must not be offered.

## Shipped
- Section language: `<img>` takes `border-radius`, `border` (`2px solid #RRGGBB`, `dashed`, or
  none) and `opacity`, as `<x-shape>` does (`section_format.py`, `sections.py`).
- In the deck they are the picture's own properties: the radius is a clip the converter maps to a
  rounded-rectangle geometry, the border is the picture's outline (`<a:ln>`, which follows the
  rounded geometry), and opacity is the blip's transparency. A second object is not added.
  `convert_image` writes the outline; the converter had none for pictures.
- The Slides panel's picture draws the border over the rounded picture
  (`section_view.py`), since the browser does not stroke an `<image>`.
- The picture panel has an Appearance section: opacity, radius, border style, width and colour
  (the rows are shared with the shape panel). The model's Slides guide names the three.
- Tests: `tests/test_deck_picture_styles.py` (the built deck's geometry, outline, dash and
  transparency; a plain picture is unchanged; the panel's drawing; a bad border is refused).

## Not verified
- Checked in Chromium against a live server (radius, border and opacity set in the panel reached
  the saved page and the stage), not in PowerPoint. The exported XML was read, not opened.
- A rounded picture with `contain` fit keeps the clip at the box, as before for any clip.

## Follow-ups
- Effects (shadow) and Advanced remain open (plan.md).
