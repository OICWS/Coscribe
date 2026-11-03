# The Code tab writes any property into an artboard element's own style (shipped)

Why: the Properties tab edits only the properties a person changes by eye. Anything else (letter
spacing, a border, a design variable as a colour) still meant asking coscribe.

## Shipped
- On the Code tab, **This element** is a field holding the element's own style, written as CSS
  (`name: value;`).
  - It saves when the field is left or on Ctrl+Enter. Escape puts the old text back.
  - A property removed from the text is removed from the element.
  - Undo takes the change back like any other edit.
- The style-sheet rules and what the element inherits stay read only. A rule can style many
  elements, so changing one there would change others too.
- The server now takes any CSS property name, custom properties (`--brand`) included. Before,
  it took only the Properties tab's list. A name or value that could break out of the attribute
  is still refused.
- The Design skill says the person can change any style property in the panel.
- Code: `OwnStyle` in `frontend/src/components/design/BoardInspector.tsx`; the typed text
  becomes changes in `styleChanges` (`frontend/src/lib/boardInspector.ts`, unit-tested).
- `design-canvas.spec.ts` writes `letter-spacing` from the Code tab, reads it in the board and
  the file, then undoes it. All 4 tests pass against a live server.

## Not verified
- Checked in Chromium on Linux only, not in the Electron app on Windows.
