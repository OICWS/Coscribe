# conversation: one conversation's turns, approvals and history, shared by the server and the CLI

## Purpose
Owns `ChatSessionLG` (`session.py`: runs a thread's turns, holds the pending approvals and the
turn counters; being split into smaller modules, so check
the directory before assuming a piece is still in it), the turn text helpers (`turn_text.py`), the approval card's before and after picture of a document edit (`edit_preview.py`), the hook commands run around tool calls (`tool_hooks.py`), the folder and skill changes between turns (`reconfigure.py`), the stream of one run to the tab (`turn_stream.py`), the tools and agent a conversation is built with (`agent_assembly.py`), the approval decision (`approvals.py`: what
runs without asking, what is refused, what waits for a person) and its resolution and resume after a reconnect (`approval_resume.py`), sub-agent and inbox reports as
turns (`subagents.py`), the line that tells it the user changed slides in the app (`deck_edits.py`) or a Word document (`docs_edits.py`, joined with it in `user_edits.py`), workflow drafting for the chat model and the save button
(`workflow_drafting.py`), the checkpointed history: replay, paging back, /compact, /clear, edit and
rewind (`history.py`), the /saveskill dialogue (`skill_save.py`), what the side panel shows
(`activity.py`, `context_usage.py`), the registry of the decks, documents and spreadsheets coscribe made, which outlives the conversation that made each one, for the Artifacts page (`artifacts.py`), and the read-only tool that lets a conversation list them (`artifact_tools.py`), the sidebar's per-thread state (`thread_meta.py`), the turn lock (`turn_lock.py`), the chat
socket's message types (`wire.py`) and where events go (`events.EventSink`). Does not own the
agent graph or its middleware (`runtime_lg`), the routes or the socket itself (`web`), or the
coordinator's tools and prompt (`coordinator.py`).

## Public interface
`ChatSessionLG`, `ThreadMetaStore`, `OPENABLE_EXTENSIONS`, `open_in_os`, `ArtifactRegistry`,
`adopt_thread`, `describe_artifact`, what the Artifacts menu does to a file (`artifact_files.py`) `rename_file`, `copy_file`, `trash_file`, `ArtifactFileError`. `wire` is imported as a
module (`from coscribe.conversation import wire`) by tests and `scripts/gen_wire_ts.py`; that
import loads the package's `__init__`, so the whole session comes with it. Tests
still reach into `session` for private helpers and to patch it; do not copy that into `src`.

## Depends on
`coscribe.code_runtime`, `coscribe.config`, `coscribe.coordinator`, `coscribe.runtime`,
`coscribe.runtime_lg`, `coscribe.tools`, `coscribe.workflows`.

## Invariants
- Only `coscribe.web` knows about HTTP: this package never imports FastAPI, Starlette or uvicorn
  (import contract, `lint-imports`); it talks to whoever is connected through `EventSink`.
- `wire.py` is stdlib only, and the chat socket's payloads match it: `tests/wire_check.py`
  validates every payload the test suite sends, and the checked-in TypeScript types equal what
  `scripts/gen_wire_ts.py` generates (`tests/test_wire_ts.py`).
- The approval precedence lives in `approvals.py` only; the session keeps the pending futures
  and their resolution (`tests/test_approval_decisions.py`).
- Imports go downward: `conversation` sits under `web` and `cli` and above `coordinator` and
  `runtime_lg` (layers contract, `lint-imports`).

## Tests
`tests/test_approval_decisions.py`, `tests/web/test_chat.py` and its `test_chat_<topic>.py`
siblings (questions, stop, modes, history, hooks, policy, events, task drafts, messaging),
`tests/web/test_prompt_injection.py`, `tests/web/test_threads.py` and its `test_thread_<topic>.py` siblings (approval preview, history,
uploads, folders, activity, files),
`tests/web/test_subagents.py`, `tests/test_subagent_tasks.py`, `tests/test_context_usage.py`,
`tests/test_wire.py`, `tests/test_wire_ts.py`, `tests/test_title_length.py`.

## Verify by hand
A real conversation on Windows with a real model: approval cards for a command and a file edit,
a sub-agent finishing while the tab is watching, /compact and /clear, the Outputs and Context
panels, a download from the browser tab saving without asking while a turn runs.

## Reviewed
2026-10-13 (first card; `session.py` was still being split, #162).
