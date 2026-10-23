# The slide stays put when the stage gets a scrollbar; a press on the grey clears the selection (shipped)

Why: selecting an element that reaches past the slide made the stage scrollable, the new scrollbar
took 12px from the stage, and the centred slide jumped. And with an element selected, only a press
on an empty part of the slide cleared the selection; a press on the stage's grey beside the slide
did nothing.

## Shipped
- `SlideStage`: the scroller is `overflow-scroll`, so both scrollbars always take their room and
  none appears or goes away on selection. An unused track draws nothing and the arrows of a
  disabled one are hidden (`index.css`, `.slide-stage`).
- `SlideEditor`: a press on the stage outside the slide clears the selection. A press on the
  scrollbar does not (the press target's offset is past the client box).
- `tests/e2e/slides-stage.spec.ts` (in the nightly list): the slide's box is the same after the
  stage becomes scrollable, and a press on the grey clears the selection while a press on the
  scrollbar does not. It runs Chromium with scrollbars on; Playwright's default hides them, which
  would hide what the cases are about. The first case fails on `overflow-auto`.

## Not verified
- Windows and the desktop app, whose scrollbar thickness may differ from the 12px styled here.
- Canvas view uses the same scroller, so it also keeps both scrollbars.

## Follow-ups
- Title-bar panel buttons the person can pin or move into a menu (asked separately).
