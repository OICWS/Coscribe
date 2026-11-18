# Changing a provider's default model keeps its saved key (shipped)

Why: on Settings > Providers, saving a change to an added provider (its default model, or a
custom one's base URL) failed with "API key cannot be blank" unless the key was typed again,
because `POST /api/providers` required one (`docs/log/2026-11-17-providers-page-redesign.md`).

## Shipped
- `web/routes/settings/providers.py`: a blank `api_key` keeps the saved key: for a built-in
  provider the one already in the environment, for a custom one the entry's stored secret in
  `providers.json`, resolved for the live context-window client. A provider without a saved key
  is still rejected with "api_key cannot be blank"; a key in the OS keychain that can't be read
  here asks for it again instead of failing the request.
- Frontend: `formProblem` (`settings/providers/catalog.ts`) asks for a key only when none is
  saved, and the key field says "Leave blank to keep it."
- Tests: `tests/web/test_settings.py` (a model-only change keeps the key, built-in and custom; a
  new provider with a blank key is rejected) and `settings/providers/catalog.test.ts`.

## Not verified
- On Windows, in the desktop app, and with a key held in the Windows Credential Manager.
