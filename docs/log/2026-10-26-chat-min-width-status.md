# The conversation's minimum width reserves room for the running time and tokens (shipped)

Why: the composer toolbar shows "12m 34s · 128.5k tokens" only while a turn runs. The minimum
width (2026-10-24-chat-min-width) was measured while idle, so a turn that started with the
conversation already at its narrowest made the toolbar overflow.

## Shipped
- `lib/composerWidth.ts` counts the status slot at 150px when it is not showing (and its real
  width when it is, if larger), so the minimum is the same before, during and after a turn.

## Not verified
- The context ring and a real Windows window; at 1000px with the Browser panel open the
  conversation stays 563px wide idle and running (was 544px idle).
