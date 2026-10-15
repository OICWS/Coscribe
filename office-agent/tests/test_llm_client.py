import pytest

from coscribe.runtime import llm_client
from coscribe.runtime.llm_client import LLMClient


def _live(monkeypatch: pytest.MonkeyPatch, lookup) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setitem(llm_client._LIVE_LOOKUPS, "fake", lookup)


def test_get_context_window_uses_the_providers_live_lookup_when_available(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: list[str] = []

    def lookup(model: str) -> int:
        seen.append(model)
        return 999_000

    _live(monkeypatch, lookup)

    assert LLMClient().get_context_window("fake:model-x") == 999_000
    assert seen == ["model-x"]


def test_get_context_window_falls_back_when_provider_has_no_live_lookup() -> None:
    client = LLMClient()

    assert client.get_context_window("anthropic:claude-3") == 200_000
    assert client.get_context_window("openai:gpt-4o") == 128_000
    # Real, user-reported bug: deepseek-flash (1M-token context, verified against
    # api-docs.deepseek.com) fell through to the generic 128k default, so the
    # context-window ring showed an 8x-too-small number.
    assert client.get_context_window("deepseek:deepseek-flash") == 1_000_000
    assert client.get_context_window("x:some-unknown-model") == 128_000


def test_get_context_window_falls_back_when_live_lookup_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def lookup(model: str) -> int:
        raise RuntimeError("network hiccup")

    _live(monkeypatch, lookup)

    assert LLMClient().get_context_window("fake:model") == 128_000


def test_gemini_without_a_key_falls_back_instead_of_raising(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

    assert LLMClient().get_context_window("gemini:gemini-3.1-flash-lite") == 128_000


def test_gemini_lookup_reads_the_models_input_token_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # The real SDK client is built (no network at construction); only the API call is
    # replaced. A fake key is enough.
    from google import genai

    monkeypatch.setenv("GEMINI_API_KEY", "fake-key-for-construction-only")
    asked: list[str] = []

    class _Models:
        def get(self, *, model: str):  # type: ignore[no-untyped-def]
            asked.append(model)
            return type("M", (), {"input_token_limit": 1_048_576})()

    monkeypatch.setattr(genai.Client, "models", property(lambda self: _Models()))

    assert LLMClient().get_context_window("gemini:gemini-3.1-flash-lite") == 1_048_576
    assert asked == ["gemini-3.1-flash-lite"]


def test_a_custom_provider_named_like_a_built_in_is_not_asked_the_built_ins_api(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def lookup(model: str) -> int:
        raise AssertionError("the built-in lookup must not run")

    _live(monkeypatch, lookup)
    client = LLMClient(custom_providers={"fake": {"base_url": "https://x/v1", "api_key": "k"}})

    assert client.get_context_window("fake:model") == 128_000


def test_deregistering_a_custom_provider_restores_the_built_in_lookup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _live(monkeypatch, lambda model: 42_000)
    client = LLMClient()
    client.register_custom_provider("fake", {"base_url": "https://x/v1", "api_key": "k"})
    assert client.get_context_window("fake:model") == 128_000

    client.deregister_custom_provider("fake")

    assert client.get_context_window("fake:model") == 42_000
