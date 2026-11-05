# Side calls on a small model; a provider key alone is enough to start (shipped)

Why: step 3 of #819 ("no complex setup"). Every title and next-message suggestion called the conversation's own model, often a provider's largest. A first run also needed a model name typed in, even when the person had already given a key.

## Shipped
- `Settings.side_model` (`COSCRIBE_SIDE_MODEL`). Empty picks the smallest model of the conversation model's provider (`config.SIDE_MODELS`):
  - Anthropic: `claude-haiku-5-5`
  - OpenAI: `gpt-6-luna`
  - Gemini: `gemini-3.5-flash-lite`

  These were checked on each vendor's model page on 2026-11-05. A provider the user added keeps its own model.
- The title and the suggestion use it through `AgentAssembly.side_model`, falling back to the conversation's model, so a key without access to the small model still gets a title.
- Compaction and the auto reviewer stay on the conversation's model. A summary that drops a request, or a reviewer that waves through a risky call, costs more than it saves.
- `default_model` unset or empty: the first provider with a key (Anthropic, OpenAI, Gemini, in that order) gives its recommended model (`config.DEFAULT_MODELS`): `claude-opus-5-5`, `gpt-6-astra`, `gemini-flash-latest`. The setup page only appears when there is no key at all.
- `.env.example` says both.

## Not verified
- None of the three vendors' accounts, so none of the small models has answered a real call from here. The fallback is tested with a model that fails.
- A real Windows first run with only a key in `.env`.

## Follow-ups
- The provider catalog's Anthropic default (`claude-opus-5`) and the setup page's example models are older than the models above. That is a separate change.
