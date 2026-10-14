"""How hard the model thinks: one scale for every model, mapped to what each one supports.

The user picks one of six levels. Providers offer fewer and name them differently (Anthropic's
`output_config.effort`, OpenAI's and DeepSeek's `reasoning_effort`, Gemini's `thinking_level`), so a
level runs as the nearest one the model supports at or below it: above a model's top it runs as
the top, in a gap it runs as the level below (cheaper), and below a model's lowest as its lowest.
A model whose levels are not known gets nothing: an unknown request field can be refused.

The level is a request parameter, never part of the prompt or the tools (decision 0001).
"""

from __future__ import annotations

import re
from typing import Any

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
_GEMINI_THINKING = re.compile(r"^gemini-(2\.5|[3-9])")
_GEMINI_LEVELS = ("low", "medium", "high")
_GEMINI_EXCEPTIONS = {"gemini-3-pro-preview": ("low", "high")}


def effort_levels(model: Any) -> tuple[str, ...] | None:
    """The levels this chat model accepts, lowest first; None when it takes no effort setting
    or its levels are not known."""
    kind = type(model).__name__
    name = str(getattr(model, "model_name", None) or getattr(model, "model", "") or "")
    if kind == "ChatAnthropic":
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
    if kind == "ChatGoogleGenerativeAI":
        name = name.removeprefix("models/")
        if name in _GEMINI_EXCEPTIONS:
            return _GEMINI_EXCEPTIONS[name]
        return _GEMINI_LEVELS if _GEMINI_THINKING.match(name) else None
    return None


def runs_as(level: str, supported: tuple[str, ...] | None) -> str | None:
    """The provider level a chosen `level` runs as; None when the model takes none."""
    if level not in LEVELS:
        raise ValueError(f"effort must be one of {', '.join(LEVELS)}, got {level!r}")
    if not supported:
        return None
    at_or_below = [s for s in supported if _RANK[s] <= _RANK[level]]
    return at_or_below[-1] if at_or_below else supported[0]


def with_effort(model: Any, level: str) -> tuple[Any, str | None]:
    """A copy of `model` that sends `level` as the nearest level it supports, and that level;
    the model unchanged and None when it takes no effort setting."""
    effective = runs_as(level, effort_levels(model))
    if effective is None:
        return model, None
    field = (
        "thinking_level" if type(model).__name__ == "ChatGoogleGenerativeAI" else "reasoning_effort"
    )
    # model_copy does not validate: langchain-google-genai types thinking_level as low | high
    # only, while the API and google-genai (ThinkingLevel.MEDIUM) take medium too.
    return model.model_copy(update={field: effective}), effective


def _ordered(levels: Any) -> tuple[str, ...]:
    known = {str(level) for level in levels}
    return tuple(level for level in _API_ORDER if level in known)
