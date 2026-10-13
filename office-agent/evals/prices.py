"""Price per million tokens, as listed on https://api-docs.deepseek.com/quick_start/pricing
(checked 2026-10-13; off-peak, which is when a run is meant to happen)."""

from __future__ import annotations

PRICES_PER_MILLION = {
    "deepseek-flash": {"input_cache_hit": 0.003, "input_cache_miss": 0.15, "output": 0.6},
}


def cost(model: str, input_tokens: int, cached_tokens: int, output_tokens: int) -> float | None:
    """The cost in the listed currency, or None for a model without a price here."""
    price = PRICES_PER_MILLION.get(model.split(":", 1)[-1])
    if price is None:
        return None
    return (
        cached_tokens * price["input_cache_hit"]
        + (input_tokens - cached_tokens) * price["input_cache_miss"]
        + output_tokens * price["output"]
    ) / 1_000_000
