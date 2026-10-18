# Slides editing, part 5a: inserting a text box, picture, table or shape

Why: the insert card at the top left of the mockups (design §4, issue #431).

## Shipped
- The card at the stage's top left: add a text box, insert a picture, a table or a shape
  (rectangle, rounded rectangle, ellipse, triangle, arrow, line). The new element lands in the
  middle of the slide, selected; a text box reads "Text", ready to type over. Editing starts on
  the current slide if it had not.
  - A table is 3 × 3 with a header row in the slide's accent colour (its most used colour that is
    not the background, the text colour or white).
  - A shape is filled with that colour; a line is drawn with it.
  - A picture is fitted into 800 × 600 px, keeping its proportions.
- `POST /api/threads/{id}/slides/assets` (form: `path`, `file`) and `add_slide_asset`: the picture
  is kept in the deck's `assets/` folder under a free name and its `src` and size returned. Only
  PNG, JPEG, GIF and WebP pictures of 15 MB at most are taken.
- Tests: the asset store (names, a second copy, refusals) and its route.

## Checked
- In Chromium against a live server, slide 5 of the Q3 deck: a text box added and typed into, an
  ellipse, a table and an uploaded picture inserted; each saved and drawn by the server.

## Not verified
- The Windows file picker in the Electron app.
