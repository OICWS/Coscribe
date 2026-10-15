"""The context-window lookup behind the UI's usage indicator: conversation/session.py's
send_state and web/app.py use it purely to show a number, never for a model call. Real
generation goes through runtime_lg's LangChain chat models.
"""

from __future__ import annotations

import os
from collections.abc import Callable


def _gemini_context_window(model: str) -> int:
    """The model's real max input-token limit, straight from the Gemini Developer API."""
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("Gemini API key is missing (GEMINI_API_KEY)")
    # Lazy: the SDK is only needed when a Gemini model is selected.
    from google import genai

    # Bound to a name: a client garbage-collected mid-call closes its HTTP client.
    client = genai.Client(api_key=api_key)
    limit = client.models.get(model=model).input_token_limit
    if limit is None:
        raise ValueError(f"the API reported no input-token limit for {model!r}")
    return int(limit)


# Providers that can report a real number. Keyed like the "provider:model" prefix.
_LIVE_LOOKUPS: dict[str, Callable[[str], int]] = {
    "gemini": _gemini_context_window,
}

# Unverified, best-effort fallback for get_context_window() -- only used
# when the provider itself can't report a real number (currently just
# Gemini can, via GeminiProvider.get_context_window's live API lookup).
# These are rough, may drift as vendors change their models, and should
# not be trusted as precise -- update as better information turns up.
_FALLBACK_CONTEXT_WINDOWS: list[tuple[str, int]] = [
    ("claude", 200_000),
    ("gpt", 128_000),
    ("o1", 128_000),
    ("o3", 128_000),
    # Verified live against api-docs.deepseek.com/quick_start/pricing/
    # (2026-09-18): both deepseek-flash and deepseek-v4-pro advertise a 1M
    # token context window. Without this entry every DeepSeek model fell
    # through to _DEFAULT_CONTEXT_WINDOW (128_000) -- a real, live-reported
    # UI bug (the context-window ring showed "78.9k / 128.0k" for a model
    # that actually has ~8x that headroom).
    ("deepseek", 1_000_000),
]
_DEFAULT_CONTEXT_WINDOW = 128_000


class LLMClient:
    def __init__(self, custom_providers: dict[str, dict[str, str]] | None = None) -> None:
        """`custom_providers` is a {name: {"base_url", "api_key"}} map of user-added
        OpenAI-compatible providers (see runtime/provider_config.py). They have no live
        lookup, so only their names matter here: a custom provider named like a built-in
        one (say "gemini") is not asked the built-in's API."""
        self._custom_providers = custom_providers or {}

    def register_custom_provider(self, name: str, config: dict[str, str]) -> None:
        """Called by web/app.py's POST /api/providers right after it persists the entry."""
        self._custom_providers[name] = config

    def deregister_custom_provider(self, name: str) -> None:
        """Undo register_custom_provider (web/app.py's DELETE /api/providers/{name})."""
        self._custom_providers.pop(name, None)

    def get_context_window(self, model: str) -> int:
        """Best-effort max input-token size for `model`; never raises.

        Asks the provider's API where it has one (Gemini). Anything else, or a failed
        lookup (no key, network), gets the estimate from `_FALLBACK_CONTEXT_WINDOWS` or
        `_DEFAULT_CONTEXT_WINDOW`. This feeds a UI indicator, so it is never worth
        breaking a turn over.
        """
        provider_key, _, model_name = model.partition(":")
        live_lookup = (
            None if provider_key in self._custom_providers else _LIVE_LOOKUPS.get(provider_key)
        )
        if live_lookup is not None:
            try:
                return live_lookup(model_name)
            except Exception:  # noqa: BLE001 -- any failure just falls through to the estimate
                pass
        lowered = model.lower()
        for needle, size in _FALLBACK_CONTEXT_WINDOWS:
            if needle in lowered:
                return size
        return _DEFAULT_CONTEXT_WINDOW
