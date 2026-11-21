# A provider's models, and the picker that offers them (shipped)

Why: part 2 of decision 0055. A provider offered one model, its default, and nothing said what a
model could do; now the person turns on the models they want and sees each one's capabilities.

## Shipped
- A provider has several models turned on and a default among them: `models` and `default_model`
  in `providers.json`, `COSCRIBE_<PROVIDER>_MODELS` and `_DEFAULT_MODEL` in `.env` for a built-in.
  One saved with only a default still has that one. Saving with no model is refused.
- `GET /api/providers` gives each provider's models as rows (`web/provider_catalog.py`
  `model_row`): images, effort levels, context window, tool calls, kind, and whether the bundled
  catalog lists it. `POST /api/providers/models` answers with the same rows; for Anthropic and
  Gemini it lists the catalog's models (`runtime.models.provider_models`), since neither serves
  an OpenAI-compatible `/models`.
- Settings > Providers: a provider's page has a Models section (a checkbox and marks per model, a
  filter past 12, the non-chat models folded away, a typed model ID, the default). The list
  column shows the default and how many more are on.
- The composer's model pill groups the turned-on models by provider with the same marks; the
  General tab's default model, a scheduled task's model and a run's investigation model offer the
  same list.
- `.github/workflows/model-catalog.yml`: a manual run now opens or updates the pull request too.

## Not verified
- The page and the pill in the desktop app on Windows; checked by type check, unit tests and the
  route tests only.
- A manual run of the catalog job: it runs on `main` once this is merged.

## Follow-ups
- The protocols (Responses, Anthropic Messages), the effort levels from the catalog in
  `runtime_lg/effort.py`, and pasting a vendor's setup (decision 0055).
