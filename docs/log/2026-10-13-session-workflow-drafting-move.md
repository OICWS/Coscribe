# Split ChatSessionLG, part 3: workflow drafting moves to conversation/workflow_drafting.py (shipped)

Why: part 3 of #162. Drafting, revising and testing a fixed workflow from a conversation is one
job with its own state (drafts live in the conversation's tool results) and does not belong in
the turn loop. This is a move; no behaviour changes.

## Shipped
- `conversation/workflow_drafting.py`: `WorkflowDrafting` holds `_build_draft_workflow_tool`,
  `_build_revise_workflow_tool`, `_build_test_workflow_tool`, `_workflow_to_change`, `_send_live`,
  `workflow_context` and `draft_workflow`; `_draft_from` and `_page_now` move with them. What it
  needs from the session is the `WorkflowDraftingHost` protocol.
- `ChatSessionLG` keeps the public `workflow_context` and `draft_workflow` (called from `web/` and
  `runtime_lg/scheduled_tasks.py`) and the three `_build_*_workflow_tool` methods as one-line
  delegates.
- Two seams stay on the session because tests patch them there: `_new_draft_id` (module level,
  reached through `_next_draft_id`) and `resolve_chat_model` (reached through `_resolve_model`).
- `tools` exports `BROWSER_HOST` and `page_screenshot`, so the new module adds no `deep_imports`
  entry.
- `session.py` 3,031 -> 2,769 lines; one `deep_imports` entry of `conversation.session` is gone.
- No test file changed; `tests/tool_schemas.txt` unchanged; `lint-imports` passes.
- Mutation check: making `_draft_from` find nothing fails
  `test_the_chat_model_tests_its_draft_and_fixes_what_failed_lg`.

## Not verified
- The app was not run on Windows; the web tests cover the three tools and the save-as-workflow draft.

## Follow-ups
- Parts 4 and 5 of #162: history, skill saving.
