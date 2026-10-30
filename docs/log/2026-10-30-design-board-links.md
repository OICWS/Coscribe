# A link from one artboard to another works in Play: a clickable prototype (shipped)

Why: the maintainer asked that a button on one artboard go to another, as Claude's Design does
with `<a href="Checkout.dc.html">` between artboard files. Play already let a person use one
artboard's page; a flow across artboards had no way to move.

## Shipped
- An artboard's page is served with a small script (`BOARD_LINKS` in
  `conversation/design_canvas.py`, added by `served_page`): a click on a link to another `.html`
  file of the canvas is handed to the panel by `postMessage`, since the sandboxed frame cannot
  navigate. Other links (anchors, the web) are left alone.
- In Play the panel shows the linked artboard, fitted to the panel, and stays in Play
  (`useBoardLinks`); only a message from one of the canvas's own frames counts.
- The Design skill: clickable prototypes as links between artboards (a flow seen whole), one
  artboard with states (screens that share data, such as a cart), and anchors (a long page); a link
  styled as the button, never a `<button>` inside a link.
- Tests: the served page carries the script only for an artboard (`tests/test_design_canvas.py`);
  e2e `design-canvas.spec.ts` clicks a link in Play and sees the other artboard centred, still in
  Play.

## Not verified
- On Windows in the desktop app (Chromium here).
- A model writing a linked prototype: the next Design eval adds a brief for it.

## Follow-ups
- A shared part several artboards include (a cart bar), and data shared between artboards.
