# aisuite dropped; google-genai declared as it runs (shipped)

Why: `pyproject.toml` declared `google-genai<1.5.0` while every job installed 2.13.x by hand,
because aisuite 0.1.14 pins `httpx<0.28`. aisuite was used only for the context-window lookup.

## Shipped
- `runtime/llm_client.py`: `LLMClient.get_context_window` asks the Gemini API through
  `google-genai` directly and estimates for every other provider. It never raises: a missing key
  or a failed call falls back to the estimate (before, building a provider could raise).
  A custom provider named like a built-in is not asked the built-in's API. There is no provider
  cache any more, so `invalidate_provider` and its two calls in `web/routes/settings/providers.py`
  are gone.
- The `providers` package (a vendored aisuite Gemini provider) is deleted, with its layer in
  `lint-imports`, its vendored-code exclusions and its card.
- `pyproject.toml`: `aisuite[openai,mcp]` removed; `google-genai>=2.13.0,<2.14.0`,
  `httpx>=0.28.1` and `mcp` declared. One `pip install` now resolves; the hand-run
  `pip install -U google-genai` is gone from the CI, desktop, Windows and mutation workflows and
  the session-start hook. Dependabot keeps ignoring google-genai (2.14 removed
  `Part.thought_signature`).
- `langchain-google-genai>=3.2.0,<4`: with aisuite gone the resolver picks 4.x, whose
  `ChatGoogleGenerativeAI` has no `thinking_level` field, so `runtime_lg/effort.py` would set
  nothing (`test_gemini_sets_its_thinking_level_medium_included` fails). The old two-step install
  had always landed on 3.2.0; the bound now says so. Moving to 4.x (`thinking_config`) is its own
  change.
- `tests/test_coordinator.py` checked the tool schemas with aisuite's converter; it uses
  LangChain's `convert_to_openai_tool` now and reads an optional parameter's `anyOf`.
- Tests: `tests/test_llm_client.py` rewritten for the new shape, with the real SDK client built
  and only the API call replaced.

## Not verified
- A real Gemini `models.get` call (no key here), and a Windows install. Provider chat turns are
  unchanged: they never went through aisuite.
