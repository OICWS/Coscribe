"""Explicit, unsaved probes through the model adapter used by conversations."""

from __future__ import annotations

import asyncio
from secrets import token_hex
from typing import Any

from langchain_core.messages import HumanMessage, ToolMessage, message_chunk_to_message
from openai import APIConnectionError, APIError, APIStatusError, APITimeoutError

from ....runtime_lg import extract_text, resolve_chat_model

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
    async for chunk in model.astream(messages):
        result = chunk if result is None else result + chunk
    return result


async def check_provider_connection(
    config: dict[str, str], model_id: str, tool_calling: bool
) -> str | None:
    """Return an error safe to display, or None when the requested capability passed."""
    stage = "reply"
    try:
        async with asyncio.timeout(30):
            model = resolve_chat_model(f"probe:{model_id}", {"probe": config})
            if not tool_calling:
                reply = await _stream_message(model, [HumanMessage("Reply with the word OK.")])
                if reply is None or not extract_text(reply.content).strip():
                    return "The provider did not stream a text reply."
                return None

            stage = "tool call"
            model = model.bind_tools([_TOOL])
            prompt = HumanMessage(
                "Call connection_check once, then reply with its verification code."
            )
            call_message = await _stream_message(model, [prompt])
            calls = call_message.tool_calls if call_message is not None else []
            if len(calls) != 1 or call_message.invalid_tool_calls:
                return "The model did not return a single valid tool call."
            call = calls[0]
            if call["name"] != "connection_check" or call["args"] or not call.get("id"):
                return "The model returned an unexpected tool call."

            stage = "tool result"
            code = token_hex(4)
            result = ToolMessage(content=code, tool_call_id=call["id"], name="connection_check")
            reply = await _stream_message(
                model, [prompt, message_chunk_to_message(call_message), result]
            )
            if reply is None or code not in extract_text(reply.content).lower():
                return "The model did not confirm the tool result in its reply."
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
        return f"The provider could not complete the {stage}. Check the API format and model ID."
