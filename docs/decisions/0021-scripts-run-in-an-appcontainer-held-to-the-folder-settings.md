# 0021: Scripts run in an AppContainer held to the folder settings

Status: accepted (2026-10-23, by the maintainer and Allen on issue #560). Supersedes the "no OS
sandbox" part of 0002; approvals, risk tiers and the audit from 0002 stay.

## Context
0002 left approvals as the only barrier: a script could read any file, use the network and get
past the write guard. The prototype (#561) showed that a script venv runs in a Windows
AppContainer, that folders granted to capability SIDs hold for the script and its children, and
that Codex's own Windows sandbox cannot hold our folders on most machines.

## Decision
- Model-written code (`run_python_script`, `run_node_script`, background scripts and commands)
  runs in one AppContainer. coscribe's own process and its trusted tools (file tools, Office
  COM, web tools) stay outside and enforce the folder settings themselves.
- Each folder is granted once to a capability derived from its path: read-only `RX`, read-write
  `RX,W` without DELETE. A run holds only its conversation's capabilities. Deletes go through a
  trusted tool (to the recycle bin), renames through `move_file`.
- A self-test per machine (cached per Windows version and interpreter) decides whether the
  container is used. Where it fails, scripts are off unless the person opts in, per conversation,
  to run without isolation (Edit environment > Scripts); that choice is audited.
- Network for scripts is a capability per run: on by default now, off by default once the
  per-conversation switch exists.

## Consequences
- What cannot be closed is said in the UI: FAT/exFAT volumes have no ACLs; SMB shares are
  unreachable from the container; a read-write folder is fully usable by an approved script.
- Codex's commands are turned off (edits only) until a code agent runs them in this container.
- Prompt injection is not removed; the aim is least privilege plus approvals.
