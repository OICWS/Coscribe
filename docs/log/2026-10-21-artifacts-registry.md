# Artifacts: a registry that outlives the conversation (shipped)

Why: the Artifacts list was derived from each conversation's Outputs, so deleting a conversation
removed its artifacts, and a file the conversation only edited (someone else's) was listed too.

## Shipped
- `artifacts.json` in the state dir registers each file a conversation created (`.pptx`, `.docx`,
  `.xlsx`; `build_pptx_from_pages` counts as creating). Edited or merely read files are not adopted.
- Conversations are adopted when the page is read and just before one is deleted, so deleting it
  leaves its artifacts in the list.
- `POST /api/artifacts/{id}/open` answers with the conversation that made it, or, when that one is
  gone, a new conversation working in the same folders. `GET /api/artifacts/{id}/thumbnail` draws a
  deck's first slide without a conversation.
- The page keys pins and cards by the artifact id, not by conversation and path.

## Not verified
- In the packaged app, with a real model, or with a deck from a real run.
- Playwright (`artifacts.spec.ts` has the new open route mocked; not run here).
- Artifacts made before this change are adopted from the checkpoints still present; those whose
  conversation was already deleted are not recoverable.
