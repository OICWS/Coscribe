# providers: the one vendored model-provider class

## Purpose
Holds `gemini_provider.py`, a trimmed copy of aisuite's Gemini provider (aisuite's PyPI release
lacks it). It exists only so `runtime/llm_client.py` can ask Google for a model's real
max-input-token limit (`get_context_window`, shown in the UI). Does not make model calls: real
Gemini conversations go through `langchain-google-genai` in `runtime_lg`.

## Public interface
`GeminiProvider`.

## Depends on
Nothing else in coscribe; it needs `aisuite` and, lazily, `google-genai`.

## Invariants
- `chat_completions_create` is a stub that raises: aisuite's `Provider` marks it abstract, so
  deleting it makes the class impossible to instantiate. Nothing may call it.
- The `google.genai` import stays inside `__init__`, so the SDK is only needed when used.
- The only importer is `runtime/llm_client.py`, also lazily; add no other caller.

## Tests
`tests/test_llm_client.py` (context-window lookup through `LLMClient`).

## Verify by hand
A real Gemini API key: the context window shown for a Gemini model matches Google's published limit.

## Reviewed
2026-10-14 (first card).
