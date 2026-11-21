# 0055: A provider has a protocol and many models, described by a bundled catalog

Status: accepted (2026-11-21, by the maintainer; proposed 2026-11-19, OICWS).

## Context
A provider has one default model, and the model picker offers that and nothing else (#994). A
custom provider speaks only OpenAI chat completions, so the Claude Code (Anthropic Messages) or
Codex (Responses) setup a vendor hands out can't be used. Nothing says which model sees images,
which effort levels it takes or how long its window is, except levels hand-written in
`runtime_lg/effort.py`. LangChain's model profiles cover the vendors' own models only: a
`ChatOpenAI` pointed at DeepSeek or Kimi has none (checked 2026-11-19).

## Decision
- **A provider names its protocol**: OpenAI chat completions, OpenAI Responses or Anthropic
  Messages. Others (Gemini native, Azure, Bedrock, Vertex, subscription sign-ins) each need a
  record of their own.
- **A provider has the models the person turns on**, picked from the list its key returns
  (`/models`); an ID can still be typed. The model picker lists every model turned on, grouped
  by provider. Non-chat rows (embedding, image, speech) are shown apart with the reason.
- **A model's capabilities come from, in order**: the person's own setting, a small override
  file in the repository (each row with a source and a date), the bundled catalog, and a
  conservative default (no images, no effort setting). The page says where each one came from.
- **The bundled catalog is a trimmed copy of models.dev** (MIT; input modalities, reasoning
  and its options, tool calls, window and output limits; about 110 KB compressed). The app never
  fetches it: a scheduled CI job runs the update script every two weeks and opens a pull request
  when it changed, listing the models added and the capabilities that changed.

## Consequences
- A model released after the last update works but runs on the default until the next release,
  unless the person sets its capabilities.
- `providers.json` changes shape; there is no migration (development stage).
- The effort levels in `runtime_lg/effort.py` move to the catalog and the override file.
- The provider page gains a protocol choice and a Models section with a row per model; the model
  picker shows capability marks. Discover's grid is unchanged.
