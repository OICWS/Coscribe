# Gemini no longer fails on a thinking-effort level (shipped)

Why: #315. Choosing an effort level for a Gemini model failed every turn with "Unknown field for
ThinkingConfig". langchain-google-genai 3.2.0 builds its request through a protobuf that has no
`thinking_level`.

## Shipped
- `runtime_lg/effort.py`: `effort_levels` returns None for `ChatGoogleGenerativeAI`, so the level
  picker offers nothing and the model thinks at its own default. The unused Gemini constants are gone.
- `tests/test_effort.py`: the Gemini rows expect None; a new test builds the request params and checks
  that nothing reaches the library's `thinking_level`.

## Not verified
- A live Gemini call after the change (the free key has 20 requests a day; the failure was reproduced
  before, the fix is checked by the request params).

## Follow-ups
- Move to langchain-google-genai 4.x and use `thinking_config` (in docs/plan.md).
