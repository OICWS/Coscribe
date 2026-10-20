# Slides: plain shapes from SVG pages are editable, a drawing says what it is, a table's preview has the right size (shipped)

Why: the maintainer's testing. The line, the bar in a card and the rings on an AI-made slide
could not be selected, and a table or a new shape changed look half a second after it was drawn.

## Shipped
- The SVG page to section converter turns a plain rectangle, rounded rectangle, circle, ellipse
  and line into the section's own shape (`x-shape`), with its fill, line, opacity and place, so it
  is selected, moved and styled like a shape the user drew. A group that only moves (a translate)
  and holds only such shapes and texts is split into its shapes, so a card's bar and base are
  separate. Anything else (a filter, a gradient, a dash, a line going up to the right, a named
  colour) stays a drawing as before. The built deck is the same: `test_svg_to_section.py`
  compares each shape's geometry, fill, line and alpha with the page's.
- A line may have zero width or height in a section (a horizontal or a vertical one).
- Selecting a drawing shows a note in the properties panel (move or resize it; ask coscribe or
  comment to change what it shows) instead of the slide's settings.
- The Slides panel's picture of a table or chart on a section slide drew its text at two thirds
  of the size the deck has (`view_native.py` used the page's px for a 1920 px canvas); text is now
  at the size in the file. That is why a table's text grew when it was clicked and when it was
  inserted.
- The editor draws a triangle, an arrow and a line as such before the server's picture arrives,
  not as a rectangle.

## Not verified
- Not run in a live server or the app, nor opened in PowerPoint.

## Follow-ups
- Lines cannot yet be dragged by their ends to any direction; a line going up to the right stays a
  drawing.
