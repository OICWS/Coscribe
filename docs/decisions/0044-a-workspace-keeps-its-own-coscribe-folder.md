# 0044: A workspace keeps its own `.coscribe/` folder: notes, skills and uploads

Status: proposed (2026-11-09, OICWS: "a workspace is managed like a repository, aligned with
Claude Code"). Adds a second place instructions come from beside the global `MEMORY.md`.

## Context
What a person taught coscribe about a project lived only in that conversation or in the one
global `MEMORY.md`, and a pasted screenshot landed in the folder's root as `image (3).png`.
Claude Code keeps a project's instructions and skills in the repository (`CLAUDE.md`,
`.claude/skills/`), so they travel with it; coscribe already works folder by folder.

## Decision
- **Layout.** In each folder a conversation works in: `.coscribe/memory.md` (the folder's notes),
  `.coscribe/skills/<name>/SKILL.md` (the global skills' format) and `.coscribe/uploads/`. Made
  on the first write, never for a read. `agents/`, `workflows/`, `settings.json`,
  `settings.local.json` and `mcp.json` are reserved, with Claude Code's meanings.
- **Delivery (0001).** Notes and the list of skills (name, description, path) go into the
  conversation's context note, sent again when they change; never the system prompt or a tool
  schema. The model reads a skill's `SKILL.md` with the file tools; one named like a global
  skill replaces it there. For work in that folder its notes come before the global ones.
- **Who writes the notes.** The person, in any editor, or by Save on the `remember` card, which
  offers "this folder" beside "everywhere". The file tools never write `.coscribe/memory.md`.
- **Trust.** Notes and skills are instructions from whoever can write the folder (a shared
  drive, a colleague, a script). coscribe keeps a fingerprint of what the person accepted per
  folder in its state folder; what it has not seen is not read until the person says "Use
  them", and a change made outside coscribe asks again. coscribe's own Save is accepted.
- **Uploads.** An attached file goes to `.coscribe/uploads/<kind>/` (screenshots, images,
  documents, data, other: by extension, not by a model); a pasted picture is named
  `screenshot-<date>-<time>.png`. A name never changes once the model has the path; the side
  model writes a one-line description of each into `uploads/index.jsonl` in the background.
- **The Files panel** lists `.coscribe` first. It never edits a file: a person edits in their
  own program or asks the model.

## Consequences
- A workspace's notes and skills move with the folder (a copy, a shared drive, a repository).
- A folder that can't be written gets no uploads there: they go to the state folder as before.
- Out of scope: notes coscribe writes by itself from a person's corrections.
