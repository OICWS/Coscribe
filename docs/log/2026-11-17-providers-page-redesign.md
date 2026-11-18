# Settings > Providers looks like Connectors, with logos and 12 more presets (shipped)

Why: the Providers page was a plain list and a form, hard to scan, and offered only seven
providers. The maintainer asked for a page like Connectors, each provider's own logo, and more
model services.

## Shipped
- `frontend/src/components/settings/ProvidersTab.tsx`: a "Yours" list (logo, default model,
  masked key) and a "Discover" grid of cards, with search and an Add menu (Browse Discover, Add
  custom provider), laid out like Connectors. A provider opens its own page
  (`settings/providers/ProviderPage.tsx`): logo, what it is, notes, a link to where a key is made,
  and the form that adds it or saves changes; Remove is there too.
- `settings/LogoTile.tsx` is the white logo tile Connectors already used, now shared by
  `ConnectorIcon` and `providers/ProviderIcon`.
- `web/provider_catalog.py` holds the whole catalog now (the built-in entries moved out of the
  route) and gives each entry a `title`, a `key_url` and, where it helps, `about`. New presets:
  Qwen (Model Studio), Doubao (Volcano Engine Ark), MiniMax, SiliconFlow, OpenRouter, Mistral, xAI,
  Groq, Together AI, Fireworks AI, Cerebras and LM Studio (local). Every base URL answered a
  request at `/chat/completions` on 2026-11-17 (401 or 400 without a key). Still no guessed
  default model for a third-party service.
- Logos in `frontend/src/assets/providers/`, named after the catalog name. The SVGs come from
  `@lobehub/icons-static-svg` 1.103.0 (MIT), which redraws each vendor's own mark as a vector, so
  they stay sharp at any size; a mono mark got its brand colour (black, Groq's orange).
  OpenRouter's is its own 180 px app icon from openrouter.ai, because its current mark is lime on
  black and reads poorly as a vector on a white tile. The marks remain their owners' trademarks
  and only name the service, as the connector icons do.

## Not verified
- On Windows, in the desktop app.
- Adding a key for any of the new services end to end: no account for them here. Qwen and
  MiniMax point at the mainland China endpoints; the page names the international ones.

## Follow-ups
- Changing only a provider's default model still needs its API key typed again, because
  `POST /api/providers` requires one.
