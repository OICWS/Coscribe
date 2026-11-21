# A provider's models, and the picker that offers them (shipped)

Why: part 2 of decision 0055. A provider offered one model, its default, and nothing said what a
model could do; now the person turns on the models they want and sees each one's capabilities.

## Shipped
- A provider has several models turned on and a default among them: `models` and `default_model`
  in `providers.json`, `COSCRIBE_<PROVIDER>_MODELS` and `_DEFAULT_MODEL` in `.env` for a built-in.
  One saved with only a default still has that one. Saving with no model is refused.
- `GET /api/providers` gives each provider's models as rows (`web/provider_catalog.py`
  `model_row`): native input and output modalities, effort levels, context window, tool calls,
  kind, whether the bundled catalog lists it, and the provider's title. The catalog keeps
  models.dev's output modalities where a model makes more than text (`outputs`, 344 rows added
  without a refresh). `POST /api/providers/models` lists what the provider offers this key, as the
  same rows: `/models` for an OpenAI-compatible one, Anthropic's `GET /v1/models`, Gemini's
  OpenAI compatibility layer.
- Settings > Providers: a provider's page has a Models section, a switch per model, a filter
  past 12, Make default, and a tip beside its info icon on hover: the model and provider, cards for its
  native input and output (Vision, PDF, Audio, Video, Image), effort levels and context. A typed model ID
  only when the provider can't list its models. The list column shows the default and how many
  more are on.
- The composer's model pill shows four models (the current one and the most recently picked,
  remembered in the browser) and the rest under More models, each with the same tip; the General
  tab's default model, a scheduled task's model and a run's investigation model offer the same
  list.
- `.github/workflows/model-catalog.yml`: a manual run now opens or updates the pull request too.

## Not verified
- The page and the pill in the desktop app on Windows: checked in Chromium against a local server,
  with the vendor's model list stood in for (no real keys here).
- Anthropic's and Gemini's model lists with a real key: the requests follow their API references
  (2026-11-21) and are pinned by route tests with a fake transport.
- A manual run of the catalog job: it runs on `main` once this is merged.

## Follow-ups
- The protocols (Responses, Anthropic Messages), the effort levels from the catalog in
  `runtime_lg/effort.py`, and pasting a vendor's setup (decision 0055).
