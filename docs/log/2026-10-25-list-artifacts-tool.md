# A conversation can find what earlier ones made (shipped)

Why: the Artifacts page remembers every document, deck, workbook and design coscribe made, but a
conversation could not: "write this week's report like my last one" had no path to start from.

## Shipped
- `conversation/artifact_tools.py`: the deferred, read-only tool `list_artifacts(kind, query,
  limit)`. It lists the registry's files across all conversations, newest first, with name, kind,
  path, modified time and a document's heading. A file in this conversation's folders carries its
  path there and `readable: true`; one outside them carries its full path and `readable: false`,
  and the usual read tools still refuse it, so the model says so.
- The description tells the model to call it only when the person refers to something made
  before and no path is known, never to look around or for the conversation's own folders.
- Added in `agent_assembly.py` beside the other tools the session builds, so `coordinator.py` and
  the bound tool list are unchanged (0001); `tests/tool_schemas.txt` gains one deferred tool.
- Tests: `tests/test_artifact_tool.py`.

## Not verified
- A real model using it only when needed.
- Windows.

## Follow-ups
- A file outside the conversation's folders cannot be read; adding its folder in Edit environment
  is the person's step.
