# The workflow review bar can be closed, waits for the turn to end, and a closed question drafts nothing (shipped)

Why: Allen tested drafting a workflow. The "Review and save" bar stayed at the bottom of the chat
with no way to close it. It was pinned for every intermediate draft while the model was still
testing and revising. When he closed the question card because he wasn't sure yet, the model
drafted a workflow anyway, and the bar came up.

## Shipped
- **The bar can be closed** (`components/workflow/usePinnedDraft.ts`, `PinnedDraftBar`). The ×
  hides the bar for that draft only. The inline card stays in the conversation. Each revision has
  its own draft id, so the next version's bar shows again. Closed ids are kept in localStorage
  (the last 50), so a reload doesn't bring a closed bar back.
- **The bar waits for the turn to end.** A draft the model is still testing or revising shows
  inline only. The latest version is pinned once the turn is over.
- **A closed question means "not yet" for something to review or save** (`QUESTIONS_DISMISSED` in
  `tools/bookkeeping/interaction.py`). If the model's next step would make a workflow draft or a
  scheduled task, it says in one line what it needs to know and stops. Otherwise it goes on as
  before.

## Checked
- `draftToPin` unit tests: it pins only after the turn ends, a closed draft stays closed while the
  next version shows, and it never pins a saved draft or one whose card is on screen.
- Screenshots against the stub backend show the bar with ×, and nothing after closing it. The bar
  stayed closed after a reload.

## Not verified
- What a real model does after the question card is closed. Only the instruction it reads changed.
