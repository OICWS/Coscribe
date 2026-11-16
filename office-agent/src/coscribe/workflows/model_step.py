"""Getting a model to return exactly a step's fields: the JSON schema they
make, the check of what came back, and the call that asks for them."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from langchain_core.messages import HumanMessage

from ..workflow_spec import OutputField

logger = logging.getLogger(__name__)

_JSON_TYPES: dict[str, dict[str, Any]] = {
    "text": {"type": "string"},
    "number": {"type": "number"},
    "boolean": {"type": "boolean"},
    "list": {"type": "array", "items": {}},
}


def fields_schema(fields: list[OutputField]) -> dict[str, Any]:
    return {
        "title": "step_result",
        "description": "The result of this workflow step.",
        "type": "object",
        "properties": {
            f.name: {**_JSON_TYPES[f.type], "description": f.description} for f in fields
        },
        "required": [f.name for f in fields],
        "additionalProperties": False,
    }


def field_problems(result: Any, fields: list[OutputField]) -> tuple[dict[str, Any], list[str]]:
    if not isinstance(result, dict):
        return {}, [f"expected an object with {', '.join(f.name for f in fields)}"]
    cleaned: dict[str, Any] = {}
    problems: list[str] = []
    for f in fields:
        if f.name not in result:
            problems.append(f"{f.name} is missing")
            continue
        value = result[f.name]
        if f.type == "number" and isinstance(value, str):
            try:
                value = float(value) if "." in value else int(value)
            except ValueError:
                pass
        valid = {
            "text": isinstance(value, str),
            "number": isinstance(value, (int, float)) and not isinstance(value, bool),
            "boolean": isinstance(value, bool),
            "list": isinstance(value, list),
        }[f.type]
        if valid:
            cleaned[f.name] = value
        else:
            problems.append(f"{f.name} must be {f.type}, got {type(value).__name__}")
    return cleaned, problems


def json_object(text: str) -> Any:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match is None:
        raise ValueError("no JSON object in the reply")
    return json.loads(match.group(0))


async def ask_model(
    model: Any,
    messages: list[Any],
    fields: list[OutputField],
    usage: dict[str, int] | None = None,
) -> Any:
    """Structured output through a forced tool call where the provider
    allows one; otherwise ask for bare JSON. Some refuse forced tool calls
    outright (DeepSeek's thinking mode: "does not support this
    tool_choice"), so any failure of the first route falls back to the
    second, whose own error is what gets reported. `usage`, when given,
    gains the tokens both routes' replies report."""
    try:
        structured = model.with_structured_output(
            fields_schema(fields), method="function_calling", include_raw=True
        )
        answer = await structured.ainvoke(messages)
        _add_usage(usage, answer.get("raw"))
        if answer.get("parsing_error") is not None or answer.get("parsed") is None:
            raise ValueError("the forced tool call didn't parse")
        return answer["parsed"]
    except Exception:  # noqa: BLE001 -- the JSON route below is the fallback for any refusal
        logger.info("workflow: structured output unavailable, asking for JSON", exc_info=True)
    keys = ", ".join(f"{f.name} ({f.type})" for f in fields)
    reply = await model.ainvoke(
        [*messages, HumanMessage(f"Reply with only a JSON object with keys: {keys}.")]
    )
    _add_usage(usage, reply)
    return json_object(str(reply.content))


def _add_usage(usage: dict[str, int] | None, reply: Any) -> None:
    """Sum a reply's tokens as an agent step's are: all of them, and apart the part the provider
    served from its cache."""
    reported = getattr(reply, "usage_metadata", None) or {}
    if usage is None or not reported:
        return
    usage["tokens"] = usage.get("tokens", 0) + int(reported.get("total_tokens") or 0)
    cached = (reported.get("input_token_details") or {}).get("cache_read")
    usage["cached_tokens"] = usage.get("cached_tokens", 0) + int(cached or 0)
