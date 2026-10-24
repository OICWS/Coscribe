# The conversation keeps room for the composer toolbar beside side panels (shipped)

Why: with a side panel open the conversation pane could shrink to 380px. The toolbar under the
message box (mode, Accept Edits, time/tokens, model, effort, context ring) is `nowrap`, so it was
clipped on the right, the context ring left the column of the stop button, and the box looked
out of proportion.

## Shipped
- `CHAT_MIN` in `components/dock/PanelDock.tsx` is 640 (was 380), `CHAT_ROOMY` 720 (was 560):
  panels no longer squeeze the conversation below what the toolbar needs; past that they lie over it.

## Not verified
- The context ring itself (it only shows once a turn has used tokens, which needs a model key);
  checked the layout at 1000px wide with the Browser panel open and a turn running.
- On a real Windows desktop window.

## Follow-ups
- None.
