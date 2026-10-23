# Codex's commands are off; it reads the folder and changes files with approval (shipped)

Why: #560 makes the folder settings the one limit on what coscribe runs. Codex runs its commands
unsandboxed (`danger-full-access`), so nothing held one to the conversation's folders; the
maintainer chose to turn them off rather than promise more than the code keeps (decision 0021).

## Shipped
- `code_runtime/thread.py`: a command Codex asks to run is declined without a card, and a
  `command_refused` event says so. A plain listing or read of the thread's own folder still runs
  without asking (the existing parse); a read outside it is now refused too.
- File changes from Codex's patch tool still come back as approvals, unchanged.
- Codex's instructions and `run_code_task`'s description say it can't run code, tests or builds,
  nor read an xlsx, docx or pdf, and that the conversation's own script tools run scripts.
- Settings > Capabilities > Approvals drops "Run commands without asking" and says why.
- Tests: `test_code_runtime.py` (a command and a read outside the folder are refused without
  asking), `test_code_agent.py` (no card for a command; the card, task and settings allowances now
  shown on file changes, with a fake `files` scenario), e2e `code.spec.ts`.

## Not verified
- A live Codex turn against a real model since the change: the fake app server stands in.

## Follow-ups
- Commands come back if Codex's own Windows sandbox is verified to hold its commands to the
  folder settings with the network off (#560, mechanism 3).
- `run_code_command`'s policy key, card rendering and approval branch stay for that; nothing
  reaches them now.
