# `solidify` is part of the `workflows` interface (shipped)

Why: `solidify` imported `runtime_lg.messages`, and `runtime_lg` imports `workflows`, so it was
the one deep import on the card and sat in the layer contract's `ignore_imports`.

## Shipped
- `draft_workflow`, `revise_workflow` and `render_conversation` take the replay entries
  (`serialize_history_for_ws_lg`) instead of LangChain messages; `conversation/session.py` makes
  them. `workflows` no longer imports `runtime_lg`, which removes the ignore entry in
  `pyproject.toml`.
- `DraftFailed`, `WorkflowDraft`, `draft_workflow`, `revise_workflow` are exported from
  `workflows`; `web/routes/threads.py` imports from the package. `conversation/session.py` keeps
  importing `solidify` by submodule: a ten-name import from the package takes 12 lines and the
  file is at its line-count limit (the ratchet).
- The card drops `runtime_lg` from "Depends on" and lists the four names.

## Not verified
- Drafting from a real conversation with a real model.

## Follow-ups
- `tools/scheduled_tasks.py` and `coordinator.py` (an invariant path) still import submodules.
