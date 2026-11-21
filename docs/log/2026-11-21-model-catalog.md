# The bundled model catalog from models.dev (shipped)

Why: part 1 of decision 0055. A provider's models need their capabilities (images, effort levels,
window) to be offered and labelled, and the app should not fetch them at run time.

## Shipped
- `runtime/models/catalog.json`: models.dev's 324 providers and about 10,000 models, trimmed to
  input modalities, reasoning with its effort levels or toggle, tool calls, window, output limit,
  kind and deprecated status; one line per model (2.0 MB).
- `runtime/models/catalog.py`: `model_info(model, provider=, base_url=)` finds the models.dev
  provider by the base URL's host (longest matching path when several share it, a short table
  for the vendors models.dev lists without one), or by name for a built-in; then applies
  `runtime/models/overrides.json` (empty for now).
- `scripts/update_model_catalog.py` and `.github/workflows/model-catalog.yml`: the 1st and the
  15th, a refresh that opens or updates one pull request listing the models added, removed and
  changed.

Nothing reads the catalog yet: the provider page, the model picker and `runtime_lg/effort.py`
start using it in the next parts.

## Not verified
- The scheduled job's own run: it needs the schedule (or a manual dispatch on `main`). Without a
  `MODEL_CATALOG_TOKEN` secret, the pull request it opens starts no checks by itself.

## Follow-ups
- The protocols, the provider page's Models section and the picker, and moving the effort levels
  onto the catalog (decision 0055).
