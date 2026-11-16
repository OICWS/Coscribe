"""One streamed pass of an agent graph, shared by sub-agents and workflow agent steps: the
pass fails once a model goes quiet too long, and each event can be counted on the way."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any, Protocol

from langchain_core.messages import AIMessage, ToolMessage

# A model call that hasn't sent a single chunk in this long is taken as
# hung: a stuck connection otherwise holds the run open with no end.
MODEL_STALL_SECONDS = 180.0


class RunRecord(Protocol):
    """What a run tells the record of how it went (decision 0045); the conversation, which
    owns that record, makes one per run."""

    def count(self, mode: str, chunk: Any) -> None: ...

    def failed(self, error: BaseException) -> None: ...

    def finish(self, *, stopped: bool) -> None: ...


class _NoRecord:
    def count(self, mode: str, chunk: Any) -> None:
        pass

    def failed(self, error: BaseException) -> None:
        pass

    def finish(self, *, stopped: bool) -> None:
        pass


# For a run whose owner keeps no record (tests, a host built without one).
NO_RECORD: RunRecord = _NoRecord()


def no_record(_head: dict[str, Any]) -> RunRecord:
    return NO_RECORD


class ModelStalled(Exception):
    pass


async def stream_turn(
    sub_agent: Any,
    turn_input: Any,
    child_config: dict[str, Any],
    on_update: Callable[[Any], Awaitable[None]],
    stall_seconds: float,
    running_tools: set[str],
    recorder: RunRecord | None = None,
) -> None:
    """One astream pass, failing once a model call goes `stall_seconds`
    without a token. Tool calls aren't timed: they run as long as the tool
    allows, and a slow one isn't a hung one. `running_tools` holds the
    calls still waiting on a result -- on a resume after approvals, the
    pass starts by running them. `recorder` counts the pass's model calls,
    tokens and tools."""
    stream = sub_agent.astream(
        turn_input, config=child_config, stream_mode=["updates", "messages"]
    ).__aiter__()
    try:
        while True:
            try:
                if running_tools:
                    mode, chunk = await stream.__anext__()
                else:
                    mode, chunk = await asyncio.wait_for(stream.__anext__(), stall_seconds)
            except StopAsyncIteration:
                return
            except TimeoutError:
                raise ModelStalled(
                    f"The model sent nothing for {stall_seconds:.0f} seconds, so the run "
                    "was stopped. Its connection may be stuck, or the provider overloaded."
                ) from None
            if recorder is not None:
                recorder.count(mode, chunk)
            if mode != "updates" or not isinstance(chunk, dict):
                continue
            for node_update in chunk.values():
                if not isinstance(node_update, dict):
                    continue
                for message in node_update.get("messages", []) or []:
                    if isinstance(message, AIMessage):
                        running_tools.update(str(call.get("id")) for call in message.tool_calls)
                    elif isinstance(message, ToolMessage):
                        running_tools.discard(str(message.tool_call_id))
            await on_update(chunk)
    finally:
        await stream.aclose()
