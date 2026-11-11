# The AI can click a button a narrow browser panel clips (shipped)

Why: during a workflow run the browser panel sits beside the chat and the run
view, about 540 pixels wide. A site built for a desktop window can clip a
toolbar that doesn't fit in a box that doesn't scroll; the AI's click on such
a button was clamped to the panel's edge and hit whatever sat there.

## Shipped
- When the element the AI acts on is still outside the viewport after
  scrolling, the tab is laid out 1280 pixels wide, unscaled, and the AI locates
  it again (`TabCdp.widen` in `office-agent-desktop/src/main/browserCdp.ts`).
  The panel keeps showing the page at its usual size, its left part; the page
  takes clicks beyond the panel's edge all the same. The tab goes back to the
  panel's width when the turn or run ends (`releaseTabs`). Pages whose
  elements fit are never widened.
- An element still out of view after that fails the click with a message,
  instead of clicking the nearest edge of the page.
- The per-step setup the two call sites in `browserAgent.ts` repeated is
  `TabCdp.drive`.

Checked in Electron 42 under Xvfb: a button at x=1050 inside an
`overflow: clip` box in a 540-pixel view is located as outside, the page widens
to 1280, and the click hits it; a button in view leaves the page at 540; the
release returns it to 540. A box with `overflow: hidden` needed no widening:
`scrollIntoView` scrolls it.

## Not verified
- On Windows with a real SAP WebGUI page.

## Follow-ups
- None.
