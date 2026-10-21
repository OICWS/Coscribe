# Slides: a text box takes an outer shadow (shipped)

Why: pictures, shapes and cards had Effects in the panel; text boxes did not.

## Shipped
- A text box takes `box-shadow` like the other objects: written as the text box's own outer shadow
  in the .pptx (behind the letters when the box has no background, behind the box when it has one),
  drawn in the panel's picture, and offered in the text panel's Effects section.
- The sections guide says so.

## Not verified
- How PowerPoint draws a letter shadow next to the panel's picture (the alpha follows the converter's
  for shapes).
- Not run in a live server or the app.
