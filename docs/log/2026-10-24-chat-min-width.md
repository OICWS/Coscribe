# The conversation keeps room for the composer toolbar beside side panels (shipped)

Why: with a side panel open the conversation pane could shrink to 380px. The toolbar under the
message box (mode, Accept Edits, time/tokens, model, effort, context ring) is `nowrap`, so it was
clipped on the right, the context ring left the column of the stop button, and the box looked
out of proportion.

## Shipped
- The composer measures its toolbar (items never shrink, so their widths plus gaps plus the
  composer's padding) into `lib/composerWidth.ts`; `components/dock/PanelDock.tsx` uses that as
  the conversation's minimum beside panels (between 380 and 900, was a fixed 380) and as the
  room a newly opened panel leaves it (plus 80). It follows the window font, the pickers' labels
  and whether the time and token count show; narrower, panels lie over the conversation.

## Not verified
- The context ring itself (it only shows once a turn has used tokens, which needs a model key);
  checked the layout at 1000px wide with the Browser panel open and a turn running.
- On a real Windows desktop window.

## Follow-ups
- None.
