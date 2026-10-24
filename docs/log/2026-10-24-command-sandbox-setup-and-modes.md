# The command sandbox asks for an administrator, has a mode without one, and Capabilities is re-laid out (shipped)

Why: on a real machine, Set up failed with `orchestrator_elevation_required`. Codex 0.163.0's
`sandbox setup` must already run elevated and doesn't ask Windows itself, and the runner is an
administrator, so CI never saw it. While it ran, the row only said "Working…". A person without an
administrator had no sandbox at all. The Capabilities page was hard to read.

## Shipped
- Setup and uninstall go through RunAs unless coscribe is elevated (`run_as_administrator` in
  `tools/exec/command_sandbox.py`). Setup names the person (`--user`, their `USERPROFILE`), and
  Codex's output comes back through a log.
- `GET /api/command-sandbox` reports the step setup is on: Codex's download with its progress,
  the administrator prompt, the test command. Settings shows them as a list.
- The basic (unelevated) sandbox needs no administrator: writes stay held, private folders are not
  hidden, and every command goes to the person (`conversation/approvals.py`). Decision 0022
  updated.
- Capabilities: an overview of what can run, then Scripts (Python and packages folded away),
  Commands with the three ways to run them as cards, and Codex with its version, folder and an
  Update action, then the code module. `GET /api/capabilities/folders` says where Codex and the
  packages live.
- The hover sidebar stays open while a conversation's menu or its Edit environment dialog is
  open. The mode menu's descriptions wrap instead of running past it.

## Not verified
- The administrator prompt on a standard-user laptop: the runner is an administrator.
- The re-laid-out page and sidebar were checked in Chromium on Linux, not clicked through on
  Windows.
