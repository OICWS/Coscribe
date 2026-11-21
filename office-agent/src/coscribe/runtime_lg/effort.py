"""How hard the model thinks: one scale for every model, mapped to what each one supports.

A model's levels come from the bundled model catalog (decision 0055), else from what the chat
model's library or the provider's documentation says. The effort picker offers a model its own
levels; the user's choice is kept on one six-level scale so it carries over a model switch, and
runs as the nearest level the model supports at or below it: above a model's top it runs as the
top, in a gap it runs as the level below (cheaper), and below a model's lowest as its lowest.
A model whose levels are not known gets nothing: an unknown request field can be refused.

The level is a request parameter, never part of the prompt or the tools (decision 0001).
"""

from __future__ import annotations

import re
from typing import Any

from ..runtime.models import model_info

LEVELS = ("low", "medium", "high", "extra", "max", "ultra")
DEFAULT_LEVEL = "medium"
# The providers' level names, lowest first. `extra` is the name we show for `xhigh`; `ultra` has
# no provider level of its own yet and runs as a model's highest.
_API_ORDER = ("low", "medium", "high", "xhigh", "max")
_RANK = {"low": 0, "medium": 1, "high": 2, "extra": 3, "xhigh": 3, "max": 4, "ultra": 5}

# Levels by model where the library's model profile has none. Checked against the providers'
# documentation on 2026-10-14; `none` and `minimal` are left out on purpose (`none` broke pages in
# the measurement behind decision 0010).
# DeepSeek documents no list; its API names the values it accepts when given an unknown one
# (asked 2026-10-14): none, minimal, low, medium, high, xhigh, ultra, max.
_DEEPSEEK_LEVELS = ("low", "medium", "high", "xhigh", "max")
_OPENAI_REASONING = re.compile(r"^(o[1-9]|gpt-5|gpt-6)")
_OPENAI_LEVELS = ("low", "medium", "high")


def catalog_levels(model_string: str, custom_providers: dict[str, Any]) -> tuple[str, ...] | None:
    """The levels the bundled catalog lists for a "provider:model", lowest first and only those
    on our scale (`none`, `minimal` and the like are left out); None when it lists none."""
    provider, _, name = model_string.partition(":")
    base_url = str((custom_providers.get(provider) or {}).get("base_url") or "")
    info = model_info(name, provider=provider, base_url=base_url)
    levels = _ordered(info.effort_levels) if info is not None else ()
    return levels or None


def effort_levels(model: Any, catalog: tuple[str, ...] | None = None) -> tuple[str, ...] | None:
    """The levels this chat model accepts, lowest first: the catalog's when it lists them, else
    the library's or the provider's documented ones; None when it takes no effort setting or its
    levels are not known."""
    if catalog:
        return catalog
    kind = type(model).__name__
    name = str(getattr(model, "model_name", None) or getattr(model, "model", "") or "")
    if kind in ("ChatAnthropic", "ChatGoogleGenerativeAI"):
        # Gemini: the library maps `reasoning_effort` onto `thinking_config.thinking_level`. Its
        # profile lists the levels per model and has none for 2.x, which take a token budget
        # instead and so get no level. `minimal` is not in our scale and is dropped.
        profile = getattr(model, "profile", None) or {}
        levels = profile.get("reasoning_effort_levels") if isinstance(profile, dict) else None
        return _ordered(levels) if levels else None
    if kind == "ChatDeepSeek":
        return _DEEPSEEK_LEVELS
    if kind == "ChatOpenAI":
        # Only OpenAI's own endpoint: an OpenAI-compatible provider may refuse the field.
        if getattr(model, "openai_api_base", None) is None and _OPENAI_REASONING.match(name):
            return _OPENAI_LEVELS
        return None
    return None


def runs_as(level: str, supported: tuple[str, ...] | None) -> str | None:
    """The provider level a chosen `level` runs as; None when the model takes none."""
    if level not in LEVELS:
        raise ValueError(f"effort must be one of {', '.join(LEVELS)}, got {level!r}")
    if not supported:
        return None
    at_or_below = [s for s in supported if _RANK[s] <= _RANK[level]]
    return at_or_below[-1] if at_or_below else supported[0]


def with_effort(
    model: Any, level: str, catalog: tuple[str, ...] | None = None
) -> tuple[Any, str | None, tuple[str, ...] | None]:
    """A copy of `model` that sends `level` as the nearest level it supports, that level, and the
    levels it supports; the model unchanged and None twice when it takes no effort setting."""
    supported = effort_levels(model, catalog)
    effective = runs_as(level, supported)
    if effective is None:
        return model, None, None
    return model.model_copy(update={"reasoning_effort": effective}), effective, supported


def _ordered(levels: Any) -> tuple[str, ...]:
    known = {str(level) for level in levels}
    return tuple(level for level in _API_ORDER if level in known)
