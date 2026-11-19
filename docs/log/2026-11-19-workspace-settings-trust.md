# A folder's settings and connectors wait for the person, like its notes (shipped)

Why: phase D of #926 (decision 0048) reads `.coscribe/settings.json` and `.coscribe/mcp.json`,
which can start programs and widen what runs without asking; whoever can write the folder can
write them, so they need the same acceptance as the notes and skills (decision 0044) before
anything reads them. Part 1: nothing applies them yet.

## Shipped
- A folder's fingerprint covers `settings.json` and `mcp.json`, so adding or changing either
  waits for "Use them" again. What the side panel gets for a folder also says whether it has
  settings and which connectors `mcp.json` names.
- The file tools refuse to write `.coscribe/settings.json`, `settings.local.json` and `mcp.json`,
  as they already refused `memory.md`: only the person edits them.

## Not verified
- Nothing applies the files yet, so there is nothing to see on Windows.

## Follow-ups
- Read `mcp.json` into the conversations of that workspace, and `settings.json`'s permissions
  and env; the side panel's "Use them" card names the settings and connectors.
