# Scripts are off where the isolation check failed, unless a conversation opts out (shipped)

Why: issue #560 and decision 0021. A machine whose self-test failed ran scripts as before, with the
folder guard only. Allen chose fail closed, with an explicit, audited choice per conversation to
run without isolation.

## Shipped
- `isolation.for_scripts` raises `IsolationRefused` (a `ValueError`, so the model reads why) on
  Windows when the self-test failed, unless the conversation is in `UnisolatedConversations`
  (`unisolated-conversations.json`). A Node run makes the script venv first when it is missing,
  so the check always has an interpreter. The tool descriptions say so.
- `isolation_status`: `passed`, `failed` (with the check), `untested` or `unsupported`. Reading it
  never runs the test; `POST /api/script-isolation/test` does.
- `GET`/`PUT /api/threads/{id}/scripts`: the conversation's choice. A change is written to the
  audit log as `run_scripts_without_isolation`, approved or rejected by a human.
- Edit environment > **Scripts**: the result, Test now / Test again, and only where the check
  failed, the "Run scripts without isolation" switch, saved with Save changes.

## Not verified
- On a Windows machine whose check fails (the CI runner passes it): the refusal and the switch are
  tested with the result faked.

## Follow-ups
- A "Not isolated" mark on a script's approval card in such a conversation.
- The sweep of grants at start and at uninstall (`docs/plan.md` item 4).
