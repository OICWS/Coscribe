"""Explicit, unsaved probes through the model adapter used by conversations."""

from __future__ import annotations

import asyncio
import logging
from secrets import token_hex
from typing import Any

from langchain_core.messages import HumanMessage, ToolMessage, message_chunk_to_message
from openai import APIConnectionError, APIError, APIStatusError, APITimeoutError

from ....runtime_lg import extract_text, resolve_chat_model

logger = logging.getLogger(__name__)

# Per request, not per check: reasoning models can think for most of a minute before answering.
_STEP_TIMEOUT = 60

_TOOL = {
    "type": "function",
    "function": {
        "name": "connection_check",
        "description": "Returns a verification code for the connection test.",
        "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
    },
}


async def _stream_message(model: Any, messages: list[Any]) -> Any:
    result = None
    async with asyncio.timeout(_STEP_TIMEOUT):
        async for chunk in model.astream(messages):
            result = chunk if result is None else result + chunk
    return result


async def check_provider_connection(config: dict[str, str], model_id: str) -> str | None:
    """Return an error safe to display, or None when the model called a tool and used its result.

    One check covers both, because a model that replies but cannot call tools cannot do the
    agent's work."""
    stage = "connection"
    try:
        model = resolve_chat_model(f"probe:{model_id}", {"probe": config}).bind_tools([_TOOL])
        prompt = HumanMessage("Call connection_check once, then reply with its verification code.")
        call_message = await _stream_message(model, [prompt])
        stage = "tool call"
        calls = call_message.tool_calls if call_message is not None else []
        if len(calls) != 1 or call_message.invalid_tool_calls:
            return (
                "The provider answered, but the model did not call the test tool. "
                "Coscribe needs a model that supports tool calling."
            )
        call = calls[0]
        if call["name"] != "connection_check" or call["args"] or not call.get("id"):
            return "The provider answered, but the model returned an unexpected tool call."

        stage = "tool result"
        code = token_hex(4)
        result = ToolMessage(content=code, tool_call_id=call["id"], name="connection_check")
        reply = await _stream_message(
            model, [prompt, message_chunk_to_message(call_message), result]
        )
        if reply is None or code not in extract_text(reply.content).lower():
            return "The model called the tool but did not use its result in the reply."
        return None
    except (TimeoutError, APITimeoutError):
        return f"The provider timed out during the {stage}."
    except APIConnectionError:
        return "Could not reach the provider. Check the URL, proxy, or TLS settings."
    except APIStatusError as exc:
        status = exc.status_code
        if status in (401, 403):
            return "The provider refused the credentials or access to this model."
        if status == 404:
            return "The provider could not find the endpoint or model. Check the URL and model ID."
        if status == 429:
            return "The provider rate-limited the request or the account is out of quota."
        return f"The provider returned HTTP {status} during the {stage}."
    except (APIError, ValueError, TypeError, RuntimeError, KeyError, AttributeError):
        # The message stays generic so a provider body never reaches the page; the log keeps
        # the cause, which may be a bug here rather than a wrong setting.
        logger.debug("Provider check failed during the %s", stage, exc_info=True)
        return f"The provider could not complete the {stage}. Check the API format and model ID."
