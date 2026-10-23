# A script can be started in a Windows AppContainer held to its folders (partly shipped)

Why: issue #560 makes the folder settings the real limit for scripts. The prototype (#561)
showed that a script venv runs in an AppContainer and that folder grants by capability SID hold
the contract. This is part 1: the mechanism, not yet applied to any tool.

## Shipped
- `tools/exec/_appcontainer.py`: `CreateProcessW` with `SECURITY_CAPABILITIES` and a handle list
  (only the three pipe ends are inherited), the container profile `coscribe.scripts`, capability
  SIDs from names, and a process object with the parts of `Popen` that `RunningCommand` uses.
- `tools/exec/isolation.py`: `Isolation` (writable, readable and runtime folders, network on or
  off), `FolderGrants` (one ACE per folder and access, recorded before it is written, granted
  again when a folder is made anew, `revoke`, `prune` for folders no longer named, `revoke_all`
  for uninstall), and `self_test`, cached per Windows version and interpreter. Read-write is
  `RX,W`: no delete or rename from a container.
- `RunningCommand(..., isolation=...)` starts in the container; without it, nothing changes.
- `tests/test_isolation.py`: the registry everywhere; on Windows, a real container (writes,
  delete, rename, reads, a child process, network off, Stop of the tree, the self-test, revoke).

## Not verified
- A real Windows 11 machine, a standard-user or company laptop, OneDrive folders and security
  software: CI's Windows runner is Server 2025 with an admin account.

## Follow-ups
- In `docs/plan.md`, item 4 of "Next": applying it to the tools, the settings screens, delete to
  the recycle bin, Python download, read limits and network, Codex's commands.
