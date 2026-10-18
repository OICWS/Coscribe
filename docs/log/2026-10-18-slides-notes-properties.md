# Slides editing, part 5b: speaker notes, transition and background

Why: the notes under the slide and the properties panel were read only; the design has both
written in the panel (§6, §7; issue #431).

## Shipped
- Speaker notes (the book icon) are a text box under the slide, up to 4,000 characters, saved
  into the section's `<aside>` when the box loses focus; emptied, the notes are removed.
- The properties panel changes the slide's transition (None, Fade, Push, Magic move) and its
  background, with the same colour picker as the format bar (the slide's own colours, or any
  hex). The picker opens above the field when there is no room below it.
- Each of these reads the slide, changes it and saves it in one call (`editSlide`); an open
  editor then reads the slide again. A slide that was an SVG page becomes a section on that
  save, as with any edit. What the build finds (for example text that can no longer be read on
  the new background) shows under the header.

## Checked
- In Chromium against a live server, slide 2 of the Q3 deck: notes written and saved into the
  section; the transition set to Fade; the background set from the slide's own colours, with
  the build's contrast warning shown.

## Not verified
- Typing notes with a Chinese IME on Windows.
