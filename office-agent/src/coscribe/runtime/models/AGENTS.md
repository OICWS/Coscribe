# runtime.models: what a model can do, from the bundled model catalog

## Purpose
Owns the model catalog of decision 0055: `catalog.json`, a trimmed copy of models.dev (MIT)
written by `scripts/update_model_catalog.py`; `overrides.json`, the rows found wrong there, each
with a source and a date; and `catalog.py`, which finds a coscribe provider's models.dev provider
by its base URL or built-in name and answers a model's capabilities (input kinds such as images,
reasoning, effort levels, tools, window, output limit, kind); and `web_search.json` with
`web_search.py`, which providers can search the web with the person's own key (models.dev has no
such field), each row with a source and a date. Does not own the
provider settings (`runtime/provider_config.py`, `web/`) or how a chat model is built
(`runtime_lg/`).

## Public interface
`ModelInfo`, `model_info`, `catalog_provider`, `WebSearchInfo`, `provider_web_search`. Import them from `coscribe.runtime.models`.

## Depends on
No other coscribe package.

## Invariants
- The app never fetches the catalog: `catalog.json` changes only through
  `scripts/update_model_catalog.py`, run on the 1st and 15th by `.github/workflows/model-catalog.yml`,
  which opens a pull request.
- Nothing is guessed: a provider or model the catalog doesn't list has no `ModelInfo`, and the
  caller uses the conservative default (no images, no effort setting).
- An override names a model the catalog lists (`tests/test_model_catalog.py`).

## Tests
`tests/test_model_catalog.py`.

## Verify by hand
Settings > Providers: hovering a model in a provider's Models section, or in the model picker, shows what it can do.

## Reviewed
2026-11-21 (first card).
