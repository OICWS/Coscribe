# Split ChatSessionLG, part 4: history, compact, clear, edit and rewind move to conversation/history.py (shipped)

Why: part 4 of #162. Replaying the checkpoint to a connecting tab, paging back through what
/compact folded away, /compact, /clear and the edit and rewind of the last message are all reads
and rewrites of the checkpoint, apart from the turn itself. This is a move; no behaviour changes.

## Shipped
- `conversation/history.py`: `ConversationHistory` holds `send_history`, `load_older_messages`,
  `_handle_compact`, `_handle_clear`, `_current_messages`, `handle_edit_message` and
  `handle_rewind_message` (with their `_locked` bodies). The pagination cursor
  (`_history_boundary_config`, `_history_known_message_ids`) moves off the session into the class.
  `close_orphaned_tool_calls` and the compact-note prefix move with it, since the edit and rewind
  bodies and `send_history` call them. What it needs from the session is the `HistoryHost` protocol.
- `ChatSessionLG` keeps one-line methods of the same public names (called from `web/` and `cli`),
  plus `_handle_compact`, `_handle_clear` and `_current_messages` (the turn dispatch and the skill
  save call them). The `_locked` bodies had no outside caller and left without a wrapper. Tests
  import `_close_orphaned_tool_calls` from `conversation.session`, which re-imports it.
- `runtime_lg` exports `is_steer`, `answer_every_tool_call` and `ORPHANED_TOOL_CALL_NOTE`, so no
  `deep_imports` entry is added.
- `session.py` 2,769 -> 2,389 lines; `deep_imports` of `conversation.session` went down.
- No test file changed; `tests/tool_schemas.txt` unchanged; `lint-imports` passes.
- Mutation check: rewind keeping one message too many (`human_positions[index] + 1`) fails
  `test_rewind_message_truncates_without_regenerating`.

## Not verified
- The app was not run on Windows; the web tests cover replay, paging, compact, clear, edit and rewind.

## Follow-ups
- Part 5 of #162: skill saving.
