# A deck coscribe did not build is shown, not edited (shipped)

Why: a presentation made elsewhere opened with the controls of one coscribe built: New slide,
reordering, comments, the insert bar and the properties panel, none of which can change that file,
and a slide the server could not draw showed the browser's broken-image mark.

## Shipped
- In a read-only deck the panel leaves out: the New slide button, the thumbnails' right-click menu
  and drag to reorder, the Comment buttons, the insert bar and the properties-panel toggle. The
  speaker notes are shown but cannot be typed into.
- `SlideThumb` shows "This slide can't be shown here" in place of a picture that fails to load,
  in the stage, the thumbnails, the canvas and the presenter.
- `tests/e2e/slides-foreign.spec.ts` (in `e2e.yml`): the server's answers are faked, since the
  runner has no office program to draw a foreign deck.

## Not verified
- A real foreign deck drawn by PowerPoint or LibreOffice on Windows.
- Undo and redo keys in a read-only deck are left as they were (a deck without history ignores them).

## Follow-ups
- None.
