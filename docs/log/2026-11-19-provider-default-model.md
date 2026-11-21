# A provider can't be saved without a default model; its models can be listed (shipped)

Why: the model picker offers each provider's default model and nothing else, so a custom
provider saved with the "optional" model field left blank never appeared in it, and no
catalog entry pre-fills a model.

## Shipped
- `POST /api/providers` rejects a provider with no default model (`default_model cannot be
  blank`); a blank model on an already saved provider keeps the saved one instead of dropping it.
- `POST /api/providers/models` lists the model IDs an OpenAI-compatible provider (any custom one,
  and built-in OpenAI) returns at `GET {base_url}/models`, with the typed or the saved key, and
  says why when it can't (refused key, no `/models`, nothing listed).
- The provider page's "Default model" is required, has "List the provider's models", and lists at
  once for an added provider that has no model yet; a pick fills the field, which stays free text
  (Ark endpoint IDs and the like).

## Not verified
- A real provider's `/models` from the Windows app; tested with a mock transport only.

## Follow-ups
- Providers that only offer an Anthropic-compatible or Responses-only endpoint can't be added as
  custom providers (custom ones speak chat completions only).
