# The Slides skill says how to change the user's template, a little or a lot (shipped)

Why: the maintainer asked coscribe to change the content of their own template, tables included.
The model edited a copy with a script and said there was no tool for a new table. That's true for
the edit tools, but a deck built from pages on the template can start each page from a template
slide and add native tables and charts. The skill didn't say when to take which way, and its
"not for changing a deck the user brought" line sent the model away from pages.

## Shipped
- `pptx-pages` skill, "Changing the template's own slides": a little (the slides stay; words,
  numbers, table cells, a picture, a chart) means editing a copy with the edit tools; a lot (new
  slides, a new table, another structure) means pages, each starting from the template slide whose
  look it keeps, with the slide's useful content written into the page. Check both ways before
  saying something can't be done.
- The template description marks a decoration shape that is a `table` and gives a shape's `text`.
  A page starting from that slide carries them and can't take them off, so the skill says to start
  from the slide's layout (`data-layout`) when they're unwanted.

## Not measured
- A real model's choice with the new text, on the maintainer's template. To run off-peak.
