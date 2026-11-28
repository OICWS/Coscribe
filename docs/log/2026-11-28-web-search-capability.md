# Web search shows as the provider's capability beside a model (shipped)

Why: Collins asked that a provider's web search show like the model capabilities (vision and the
rest), from the same table the search falls back through (`runtime/models/web_search.json`).

## Shipped
- Each model row the server sends (`web/provider_catalog.py`'s `model_row`) carries
  `web_search`: whether its provider has a search the free engines fall back to. It is the
  provider's, so every model of a DeepSeek provider has it.
- The model tip (model picker, Settings > Providers > Models) shows it under "Through the
  provider" as a "Web search" card with a globe, also for a model the catalog doesn't list.

## Not verified
- Looked at in Chromium on Linux (light and dark), not in the Windows desktop app.

## Follow-ups
- Anthropic, OpenAI and Gemini search as a second kind in the table (`docs/plan.md`).
