# What the model is sent is written down in a snapshot (shipped)

Why: Step 4 of the structure period (record 0009). Decision 0001 says the system prompt and the tool list bound to the model are the same for every conversation, because providers cache them by prefix. `tests/test_prompt_cache.py` pins that two conversations get the same ones, but nothing showed what they are, so a change to a tool's description or parameters went through unseen.

## Shipped
- `tests/tool_schemas.txt` is a snapshot of: the system prompt (11,048 tokens by a characters-over-four estimate, and a hash), the 22 tools bound to the model (about 4,850 tokens; each with its parameters, which are optional, and a hash of its description), and all 119 registered tools (about 36,000 tokens, matching the 35k of record 0001) with risk tier, category, core or deferred, and a description hash.
- `tests/test_tool_schema_snapshot.py` compares the current ones with it; `UPDATE_TOOL_SCHEMAS=1 pytest tests/test_tool_schema_snapshot.py` rewrites it, and the diff shows which tool changed and how big the cached prefix became. A second test builds the description for two conversations with other folders and thread ids and requires them to be identical, which also fails if any path of the conversation reaches the system prompt.
- The snapshot and its test are `CODEOWNERS` paths; record 0001's consequences name it.
- Found while writing it: the system prompt holds the skills directory path (`Your local skills directory ... is: <path>`). It is the same for every conversation of an install, so the cache is not hurt, but it differs between installs, so it is replaced by `<skills dir>` before measuring. Moving that sentence into a tool result would make the prompt identical for every user; not done here.

## Not verified
- That the snapshot is the same on Windows and on CI (a tool that is registered only on some platform or with some package would make it differ); CI's first run is the check for Linux.
- The estimate counts characters, not a provider's tokens.

## Follow-ups
- Decide whether the skills-directory sentence should move out of the system prompt.
