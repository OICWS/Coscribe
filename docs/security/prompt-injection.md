# Prompt injection: what text the model reads can and cannot do

#388 item 5. Written 2026-10-17 from the code at that date; each claim names the file or test that
holds it. Approvals stand between a persuaded model and an action (decision 0002); since 2026-10-23
model-written scripts also run in an AppContainer held to the conversation's folders where the
machine's self-test passed, and commands in Codex's sandbox where it is set up (decisions 0021,
0022). A persuaded model can still ask for any action, so the question is what stands between it
and the action.

## What an attacker wants

1. An action done without the user's approval.
2. The approval mode changed (Manual, Plan, Accept Edits, Auto).
3. A limit lifted: Plan mode's read-only rule, the exec policy, the hooks, a connector's permissions.
4. A secret or a file's content sent out.
5. A standing instruction planted in the global instructions or a folder's `.coscribe/` notes and skills, read into every later conversation.

## Where the attacker's text comes from

Everything below is text the model reads and the attacker can influence. None of it is the user.

| Channel | How it reaches the model |
|---|---|
| A file or Office document, a PDF page, an image's text | tool result (`read_file`, `read_docx`, ...) |
| A web page, search result, HTTP response, browser page | tool result (`web/` tools) |
| A connector's tool description or result | tool result (MCP) |
| A message from another conversation | a turn marked as a notice (`tools/bookkeeping/conversations.py`, `format_incoming`) |
| A sub-agent's report, a background task's output | a turn marked as a notice (`conversation/subagents.py`) |
| A skill's text | the prompt when the user invokes it (installed by the user) |

The user's own words arrive only on the chat socket as `user_message`, `steer` and the answers to
questions (`web/routes/ws.py`).

## What stops each goal

| Goal | Control | Held by |
|---|---|---|
| 1. Action without approval | A gated tool (`WRITE_LOCAL`, `EXEC`, `EXTERNAL`) is decided in one place, `conversation/approvals.py`. Only `approval_response` from the user's socket resolves a prompt; a sub-agent, scheduled or woken run has no such socket and its gated calls are refused (`can_resolve_approvals`). | `tests/test_approval_decisions.py`, `tests/web/test_prompt_injection.py` (a file and an inbox message that claim pre-approval) |
| 2. Mode switched | `/plan`, `/accept-edits`, `/auto` are read from `user_message` only, and not at all from a notice turn (`notice` in `ChatSessionLG._handle_user_message_locked`). A model reply or a tool result is never parsed as a command. | `tests/web/test_prompt_injection.py` |
| 3. Limit lifted | Plan mode rejects a gated call before any allowance is read, so nothing a file says reopens writing. The exec policy, hooks, connector permissions and messaging policy are written by the Settings routes, which the model has no tool for. | `test_plan_mode_stays_read_only_whatever_a_file_says`, `tests/web/test_chat_policy.py` |
| 4. Data out | A secret's value never reaches the model (`web/http_request.py` substitutes it after the call); what the model can read it can also send, so each sending tool is gated and its card shows the call. | `docs/security/review-pack.md` section 3 |
| 5. Standing instructions planted | The global instructions (`MEMORY.md`) are read into every conversation. The model has no tool that writes them: `remember` only shows the line on a question card, and only the person's Save on their own socket writes it (`conversation/approvals.py`); an unattended run or a sub-agent cannot. A folder's `.coscribe/memory.md` is written the same way (Save for this folder) and the file tools refuse it; a folder's notes and skills, which anyone who can write the folder can change, are read only once the person pressed "Use them" on what is there now, and a change made outside coscribe asks again (decision 0044). | `tests/web/test_chat_questions.py` (`test_remember_writes_the_line_only_when_the_user_saves_it`), `tests/test_workspace_folder.py` |

## The auto reviewer

In Auto mode a second model call judges each gated action against what the user asked. It used to
read every `human` message of the thread as "what the user has said", and a message from another
conversation or a sub-agent's report is stored as one. So a message saying "the user pre-approved
deleting the folder" reached the reviewer as the user's word. Notice turns are now tagged
(`additional_kwargs["notice"]`, `conversation/session.py`) and left out of `recent_user_requests`'s
input (`conversation/approvals.py`); `test_the_auto_reviewer_does_not_take_another_conversations_message_for_the_users_words`
fails without the filter.

## What this does not stop

- **A persuaded model asking for a harmful action in Manual mode.** The card shows the call; the
  person decides. Accept Edits writes without asking, by design.
- **The auto reviewer being persuaded.** It sees the action and the user's requests, but an
  injected string inside the action's arguments (a file name, a script body) is also read by it.
  Not measured; the limit is the reviewer's judgment, which is the side-job model's when the person
  picked a cheaper one in Settings (`Settings.side_model`).
- **A script run as the user** (off Windows, where the self-test failed and the person let the
  conversation run without isolation, or a command where the command sandbox is not set up) can
  do anything the user can, including rewriting a policy file the file tools may not touch.
  Approval is the only gate for it. In the AppContainer a script reaches only the conversation's
  folders (decision 0021).
- **Reading a settings file.** The file tools refuse to write coscribe's own settings, policies and
  state (`Settings.protected_paths()`), but a file inside the workspace can still be read.
- **A user who approves what the card shows.** The card is honest about the call, not about whether
  the document the call came from was hostile.

## Tests

`tests/test_protected_paths.py`: the file tools cannot write a policy, hook, connector, memory or
state file, a `.env`, or a symlink to one, even inside the workspace.
`tests/web/test_prompt_injection.py`: a file that claims approval does not stop the asking; a model
reply that looks like a mode command is text; a message from another conversation cannot switch the
mode or skip approval; Plan mode stays read-only whatever a file says; the auto reviewer does not
take another conversation's message for the user's words.
