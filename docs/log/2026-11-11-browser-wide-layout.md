# The AI can click buttons a narrow browser panel cuts off (shipped)

Why: during a workflow run the browser panel sits beside the chat and the run
view, about 540 pixels wide. Sites built for a desktop window, SAP's WebGUI
among them, clip a toolbar or grid that doesn't fit instead of scrolling it, so
a button such as Export was never on screen and the AI's click landed on
whatever sat at the panel's edge.

## Shipped
- While an AI turn or workflow run drives a tab, the page lays out at least
  1280 pixels wide and the panel shows it scaled down to fit
  (`TabCdp.fit` in `office-agent-desktop/src/main/browserCdp.ts`). When the
  turn or run ends the tab goes back to the panel's own width. A panel 1280
  pixels or wider is left as it is; a tab the AI works in with the panel closed
  also gets the 1280-pixel minimum.
- Mouse events are scaled to match, so the AI's clicks and the person's own
  clicks land on the same element as before.
- The AI's screenshot, the panel's "Save screenshot…" and the annotation
  capture take the whole laid-out page (`captureTab`), not the scaled picture
  in a corner of a blank image; a picked element's thumbnail uses the scaled
  rectangle.
- An element still outside the visible area after scrolling (clipped by a box
  that doesn't scroll) now fails the click with a message, instead of clicking
  the nearest edge of the page.

Checked in Electron 42 under Xvfb: a button at x=1050 in a 540-pixel panel was
missed before (the click hit the page body) and is hit with the wide layout,
with the panel shown, hidden, and at 80% zoom; the layout returns to 540 when
the run ends.

## Not verified
- On Windows with a real SAP WebGUI page and a display scale above 100%.

## Follow-ups
- None.
