# A Settings picker for the side-job model, which Auto mode's reviewer now uses too (shipped)

Why: #832. The maintainer wants to choose, from the models already configured, the model that runs
the short calls around a chat, and nothing picked to mean the default model. Until now
`COSCRIBE_SIDE_MODEL` could only be set in `.env`, an empty value silently picked the provider's
smallest model for titles and suggestions, and the Auto mode reviewer always used the chat's model.

## Shipped
- Settings > Sessions > "Model for side jobs": the configured models plus "Same as the chat's
  model" (`ConfiguredModelSelect`, now shared with Settings > Capabilities > "Model for code").
  `COSCRIBE_SIDE_MODEL` is checked as `provider:model` (or blank) and applies without a restart.
- `config.side_model_name`: the picked model, else the model it is given (the chat's own model, or
  `Settings.default_model` outside a chat). `SIDE_MODELS`, the per-provider small models, is gone:
  a cheaper model is the person's pick, not a guess.
- Auto mode's reviewer runs on `ChatSessionLG.side_model()`, with the chat's model as fallback
  when the picked one fails; both answer at temperature 0 (`auto_review._at_zero_temperature`).
  Titles and next-message suggestions use the same model as before.
- A scheduled task's one-line overview (built separately) resolves the same setting with
  `side_model_name(settings.default_model, settings.side_model)`.

## Not verified
- A real provider answering as the picked model; the tests use scripted models, including one
  that fails to show the fallback.
- The picker on a real Windows desktop build.

## Follow-ups
- Compaction stays on the chat's model: a summary that drops a request costs more than it saves.
