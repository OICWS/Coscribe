# The composer toolbar shortens its labels and hides the running time when narrow (shipped)

Why: with the conversation squeezed beside a panel the toolbar under the message box overflowed
and the context ring left the stop button's column; a measured minimum width (#608) either left
the pane wide or broke when the running time and tokens appeared mid-turn.

## Shipped
- The environment, mode and model labels truncate (`min-w-0` roots), the effort picker and the
  context ring never shrink, so the ring stays under the stop button.
- The running time and token count show only when the composer is at least 600px wide
  (container query), so a turn starting in a narrow pane changes nothing.
- `lib/composerWidth.ts` is gone; `CHAT_MIN` in `PanelDock.tsx` is 320 (was 380, #608 had 380-900 measured).

## Not verified
- The context ring itself (needs a model key) and a real Windows window; at 1000, 760 and 560px
  with the Browser panel open the toolbar never overflowed (conversation 544 / 320 / 560px).
