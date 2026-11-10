# A folder's own notes and skills in `.coscribe/` (partly shipped)

Why: what a person taught coscribe about a project was lost with the conversation or went into the
one global `MEMORY.md`. Decision [0044](../decisions/0044-a-workspace-keeps-its-own-coscribe-folder.md)
keeps it in the folder, as Claude Code keeps `CLAUDE.md` and `.claude/skills/` in a repository.

## Shipped
- `conversation/workspace_folder.py`: each folder's `.coscribe/memory.md` and
  `.coscribe/skills/<name>/SKILL.md` go into the conversation's context note (name, description
  and path of each skill; the model reads the file), never the system prompt.
- Trust: a fingerprint of the notes and every file under `skills/` per folder in
  `workspace-trust.json` (state folder). Until the person presses "Use them" under "About this
  folder" in the side panel, the context only says they exist and are not to be followed; a change
  made outside coscribe asks again. `POST /api/threads/{id}/workspace-notes` accepts.
- The `remember` card offers "Save for this folder" beside "Save everywhere"; a save into a folder
  that was accepted (or empty) stays accepted. The file tools refuse to write any
  `.coscribe/memory.md`.
- The Files panel lists `.coscribe` first.

## Not verified
- On Windows: a folder on a network share, and a `.coscribe` made by another program.

## Follow-ups
- Uploads into `.coscribe/uploads/<kind>/` with descriptions (0044's second part, `docs/plan.md`).
