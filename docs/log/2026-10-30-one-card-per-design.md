# A design is one card in the chat, not one per artboard (shipped)

Why: a design of six phone screens showed six cards in the chat ("home · Design · .html",
"discover", ...), each opening a lone page, though they are the boards of one canvas.

## Shipped
- The cards a turn ends with (`FileCards`) give a page in a `<name>.design/` folder as its canvas,
  `<name>.design.json`: one card per design, which opens the canvas
  (`madeFiles`, `canvasOfPage` in `frontend/src/lib/fileMentions.ts`).
- The skill writes the pages before the canvas, so the canvas card appears once the canvas reads,
  asking again as the turn's calls grow (`useShownFile`).
- A file name mentioned in the answer (`home.html`) is still a chip that opens that page.
- The Artifacts page already listed only the canvas (`describe_artifact` drops a board's page).

## Not verified
- Not run live with a model: the unit tests cover the mapping, not the card appearing mid-turn in a
  real window.
- A turn stopped before it wrote the canvas shows no card for its pages, and the Artifacts page
  lists those pages one by one.
