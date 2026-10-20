# Pictures, shapes and cards take an outer shadow (shipped)

Why: the mockups' Effects section. A shadow is the one effect the deck carries as the object's own
effect, so it is the part of Effects that can be offered.

## Shipped
- Section language: `box-shadow: Xpx Ypx BLURpx #RRGGBB [opacity]` on `<img>`, `<x-shape>` and a
  container's card look (`sections.py`, `section_layout.py`). It becomes the SVG filter the
  converter already maps to an outer shadow; the offset and blur are in the section's px and are
  converted to the SVG pages' px first, so 24px of blur is 24px in the deck. The converter takes a
  quarter off the opacity because PowerPoint draws a shadow heavier than the preview.
- Effects section in the properties panel for a picture, a shape (not a line) and a container:
  shadow none or outer, offset X and Y, blur, colour, opacity. The Slides panel shows it from the
  same drawing as the deck.
- The model's Slides guide names `box-shadow`.
- Tests: `tests/test_deck_picture_styles.py` (the built XML for a picture, a shape and a card, a
  bad shadow refused), `lib/slideShadow.test.ts`.

## Not verified
- Checked in Chromium against a live server (a picture's shadow set in the panel reached the
  saved page and the stage), not in PowerPoint. How heavy PowerPoint draws it is the converter's
  own estimate.

## Follow-ups
- Text boxes take no shadow (their text is placed by the engine, not drawn as a shape). Glow,
  reflection and blur effects have no section-language form.
- "Advanced" in the mockups has no part that exports, so it is not offered.
