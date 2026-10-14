"""One effort scale for every model (`runtime_lg/effort.py`): what each level runs as, and that
the real chat model classes put it in the request field their provider reads."""

from __future__ import annotations

from typing import Any, get_args

import pytest

from coscribe.conversation import wire
from coscribe.runtime_lg.effort import LEVELS, effort_levels, runs_as, with_effort
from coscribe.runtime_lg.providers import resolve_chat_model

_PROVIDERS = {
    "deepseek": {"base_url": "https://api.deepseek.com/v1", "api_key": "k"},
    "kimi": {"base_url": "https://api.moonshot.cn/v1", "api_key": "k"},
}


@pytest.fixture(autouse=True)
def _keys(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GOOGLE_API_KEY"):
        monkeypatch.setenv(name, "k")


def _model(name: str) -> Any:
    return resolve_chat_model(name, _PROVIDERS)


@pytest.mark.parametrize(
    ("supported", "expected"),
    [
        # A model with every level: each runs as itself, ultra as the top.
        (
            ("low", "medium", "high", "xhigh", "max"),
            ["low", "medium", "high", "xhigh", "max", "max"],
        ),
        # Three levels: above the top runs as the top.
        (("low", "medium", "high"), ["low", "medium", "high", "high", "high", "high"]),
        # A gap runs as the level below, the cheaper one.
        (("low", "high", "max"), ["low", "low", "high", "high", "max", "max"]),
        # Nothing at or below: the model's lowest.
        (("high", "max"), ["high", "high", "high", "high", "max", "max"]),
        (None, [None] * 6),
    ],
)
def test_each_level_runs_as_the_nearest_supported_one_at_or_below_it(
    supported: tuple[str, ...] | None, expected: list[str | None]
) -> None:
    assert [runs_as(level, supported) for level in LEVELS] == expected


def test_an_unknown_level_is_refused() -> None:
    with pytest.raises(ValueError, match="effort must be one of"):
        runs_as("turbo", ("low",))


@pytest.mark.parametrize(
    ("model", "levels"),
    [
        ("anthropic:claude-opus-5-5", ("low", "medium", "high", "xhigh", "max")),
        ("anthropic:claude-sonnet-4-6", ("low", "medium", "high", "max")),
        ("anthropic:claude-3-5-haiku-latest", None),
        ("deepseek:deepseek-flash", ("low", "medium", "high", "xhigh", "max")),
        ("kimi:kimi-k2", None),
        ("openai:gpt-5.5", ("low", "medium", "high")),
        ("openai:gpt-4o", None),
        ("gemini:gemini-3.5-flash", ("low", "medium", "high")),
        ("gemini:gemini-3-pro-preview", ("low", "high")),
        ("gemini:gemini-2.0-flash", None),
    ],
)
def test_the_levels_each_model_takes(model: str, levels: tuple[str, ...] | None) -> None:
    assert effort_levels(_model(model)) == levels


def test_claude_sends_output_config_effort() -> None:
    model, level = with_effort(_model("anthropic:claude-opus-5-5"), "extra")

    assert level == "xhigh"
    assert model._get_request_payload("hi")["output_config"] == {"effort": "xhigh"}


def test_deepseek_sends_reasoning_effort() -> None:
    model, level = with_effort(_model("deepseek:deepseek-flash"), "extra")

    assert level == "xhigh"
    assert model._get_request_payload("hi")["reasoning_effort"] == "xhigh"


def test_openai_sends_reasoning_effort() -> None:
    model, _ = with_effort(_model("openai:gpt-5.5"), "max")

    assert model._get_request_payload("hi")["reasoning_effort"] == "high"


def test_gemini_sets_its_thinking_level_medium_included() -> None:
    model, level = with_effort(_model("gemini:gemini-3.5-flash"), "medium")

    assert level == "medium"
    assert model.thinking_level == "medium"


def test_a_model_without_effort_is_returned_unchanged() -> None:
    original = _model("kimi:kimi-k2")

    model, level = with_effort(original, "max")

    assert model is original and level is None
    assert "reasoning_effort" not in model._get_request_payload("hi")


def test_the_wire_lists_the_same_levels() -> None:
    assert get_args(wire.Effort) == LEVELS
