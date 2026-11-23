---
title: A folder's own notes and rules
description: Let a folder tell coscribe what it holds, which skills and connectors to use, and what may run without asking.
---

A folder can carry instructions for coscribe in a `.coscribe` folder inside it. coscribe reads them for any conversation that uses the folder, once you have accepted them.

## What a folder can hold

| File | What it does |
|---|---|
| `.coscribe/memory.md` | Notes coscribe reads at the start of each conversation in this folder: what the folder is for, conventions, names. |
| `.coscribe/skills/<name>/SKILL.md` | [Skills](../customize/skills.md) that apply only in this folder. |
| `.coscribe/settings.json` | Permission rules (`allow`, `ask`, `deny`) and environment variables for scripts. |
| `.coscribe/mcp.json` | [Connectors](../customize/connectors.md) this folder uses. |

coscribe itself never writes `memory.md`, `settings.json` or `mcp.json`; only you edit them. Attachments you send are kept in `.coscribe/uploads/`.

## Accept a folder's settings

Settings from a folder could come from anyone who could write to it, so coscribe doesn't follow them until you agree. The **Task details** panel shows **What Coscribe knows about this folder**, listing the skills, connectors and rules the folder brings, grouped as **Runs without asking**, **Always asks** and **Never runs**, and any variables for scripts. Click **Use them** to accept.

If any of these files changes outside coscribe, it asks again.

## Permission rules

`.coscribe/settings.json` uses the same shape as Claude Code's settings file:

```json
{
  "permissions": {
    "allow": ["write_file(reports/*)"],
    "ask": ["run_background_command"],
    "deny": ["delete_file"]
  },
  "env": {
    "REPORT_REGION": "East"
  }
}
```

A rule is a coscribe tool name, a `*` pattern of names, or either with a pattern of its main argument in brackets, such as `write_file(docs/*)`. The rules decide only actions that would otherwise wait for your approval. **deny** wins over **ask**, and **ask** over **allow**.

Some limits always hold:

- A rule never allows an action that leaves your computer, such as sending a message through a connector; those still ask.
- A bare `*` allows nothing.
- An `ask` rule asks even in **Auto** mode.

## Variables for scripts

The `env` values in `settings.json` are passed to scripts and commands in the folder. A folder can't set variables that change which programs run or where traffic goes, such as `PATH`, proxy settings or `PYTHONPATH`.
