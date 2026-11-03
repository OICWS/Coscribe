# An artboard's text is edited in place by a double click (shipped)

Why: changing a word on an artboard meant picking the element and typing in the properties panel's
Text field, away from where the text is drawn.

## Shipped
- **Double click** on text in an artboard. If the element holds only text, a field opens right
  over it. The field has the same font, size, weight, line height, letter spacing, alignment,
  colour and padding, and it moves and scales with the canvas.
  - The page's own copy stays in place but turns transparent, so nothing around it moves.
  - The properties panel opens if it was closed, with the element picked.
- **Keys:**
  - Enter, or clicking away, writes the text into the page, the same way as the panel's Text
    field (`PUT /canvas/element`). It can be undone, and coscribe is told at its next turn.
  - Shift+Enter starts a new line.
  - Escape leaves the page as it was.
- An element that holds other elements (a row, a card) is only picked by a double click.
- How it works: `board_inspector.js`
  - It now also reports the computed text style the field copies (font style, letter spacing,
    alignment, text transform).
  - It answers a new `inspect-hide-text` message, which turns the element's text transparent and
    back.
- **Tests:** `design-canvas.spec.ts` covers:
  - a double click with the panel closed, then Escape;
  - a double click, typing and Enter, after which the file holds exactly the new text;
  - a double click on a row, which only picks it.

  All 5 tests pass against a live server.

## Not verified
- Checked in Chromium on Linux only, not in the Electron app on Windows.
- At a small zoom the field is as small as the drawn text; there is no zoom-to-edit.
