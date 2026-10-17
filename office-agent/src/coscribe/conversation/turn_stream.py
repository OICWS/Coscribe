"""One model-and-tools run (`astream`) forwarded to the tab as it happens: the model's narration,
each tool's start and result, and the running token count."""

from __future__ import annotations

from typing import Any, Protocol

from langchain_core.messages import AIMessage, AIMessageChunk, ToolMessage
from langchain_core.messages.ai import UsageMetadata
from langgraph.types import Command

from ..runtime_lg import extract_text as _extract_text
from ..runtime_lg import tool_result_value as _tool_result_value
from ..runtime_lg import unwrap_use_tool_call
from ..tools import QUESTION_TOOL_NAMES, TASK_DRAFT_TOOL_NAMES
from .events import EventSink
from .history import close_orphaned_tool_calls
from .turn_text import usage_event


class TurnStreamHost(Protocol):
    """What the stream reads and writes on the session it belongs to."""

    config: dict[str, Any]
    lg_agent: Any
    _turn_websocket: Any
    _stop_requested: bool
    _gated_tool_risks: dict[str, str]
    _pending_tool_args: dict[str, list[dict[str, Any]]]
    _last_usage_metadata: UsageMetadata | None

    async def _run_post_tool_use_hooks(
        self, name: str, args: dict[str, Any], result: Any
    ) -> None: ...

    async def _send_tool_started(
        self, name: str, args: dict[str, Any], websocket: EventSink
    ) -> None: ...


class TurnStreamer:
    def __init__(self, host: TurnStreamHost) -> None:
        self._host = host

    async def stream_turn(self, turn_input: Any, websocket: EventSink) -> str:
        """Run one `astream()` call and return only the last model response's narration.

        A call can cover several model responses when an ungated tool runs in between. Each
        response's narration already streamed live as its own bubble, so the return value
        restarts at every tool result: joining them would glue the pre-tool text onto the
        post-tool text with no separator. A gated call ends the call at the interrupt with
        no tool result, so there the return value is already one segment.

        A tool result carries no arguments, so the arguments of each call are recovered
        from the streamed model chunks and parked in `_pending_tool_args`: when the result
        arrives in this call, or at the end of the loop for a gated call whose result comes
        in the resumed call after approval.

        Stop is cooperative, checked after every chunk: it cannot cut a model call already
        in flight. The generator is closed explicitly so an abandoned one does not keep
        running in the background.
        """
        host = self._host
        agent = host.lg_agent
        config = host.config
        host._turn_websocket = websocket
        if not isinstance(turn_input, Command):
            await close_orphaned_tool_calls(agent, config)
        text_parts: list[str] = []
        accumulated: AIMessageChunk | None = None
        # The chunks of the latest model response only. Each response's usage already counts
        # the whole prompt it was sent, so summing responses would count the context twice.
        segment: AIMessageChunk | None = None
        registered_ids: set[str] = set()

        def _flush_accumulated() -> None:
            nonlocal accumulated
            if accumulated is None:
                return
            for call in accumulated.tool_calls:
                call_id = call["id"]
                if call_id is not None and call_id not in registered_ids:
                    # The stream carries the model's own use_tool call; the tool's result
                    # comes back under the real name.
                    name, args = unwrap_use_tool_call(call["name"], call["args"])
                    host._pending_tool_args[name].append(args)
                    registered_ids.add(call_id)
            # Providers number each response's tool calls from index 0 and send a call's
            # later argument pieces without its id, so adding chunks joins such a piece to
            # the first call with that index. Carried into the next response, its pieces
            # would join this response's call and the new call would lose its arguments.
            accumulated = None

        async def _capture_segment_usage() -> None:
            nonlocal segment
            if segment is not None and segment.usage_metadata:
                host._last_usage_metadata = segment.usage_metadata
                # Sent at every boundary, not only at turn end, so the token counter moves
                # during a long multi-tool turn.
                await websocket.send_json(usage_event(segment.usage_metadata))
            segment = None

        # "updates" is only for the model node's finished message: it lands before any of
        # its tool calls run, which "messages" has no event for.
        stream = agent.astream(turn_input, config=config, stream_mode=["messages", "updates"])
        try:
            async for mode, chunk in stream:
                if mode == "updates":
                    await self.announce_started_tools(chunk, websocket)
                    continue
                message, _metadata = chunk
                if isinstance(message, AIMessageChunk):
                    text = _extract_text(message.content)
                    if text:
                        text_parts.append(text)
                        await websocket.send_json({"type": "agent_delta", "text": text})
                    accumulated = message if accumulated is None else accumulated + message
                    segment = message if segment is None else segment + message
                elif isinstance(message, ToolMessage):
                    _flush_accumulated()
                    await _capture_segment_usage()
                    text_parts.clear()
                    name = message.name or ""
                    result_value = _tool_result_value(message.content)
                    args = (
                        host._pending_tool_args[name].pop(0)
                        if host._pending_tool_args[name]
                        else {}
                    )
                    await host._run_post_tool_use_hooks(name, args, result_value)
                    # A question or draft tool already has its own card; a tool_result too
                    # would add a second row for the same interaction.
                    if name not in QUESTION_TOOL_NAMES and name not in TASK_DRAFT_TOOL_NAMES:
                        # The arguments ride along so a live row can show the real filename
                        # or query; nothing else carries them for an ungated tool.
                        await websocket.send_json(
                            {
                                "type": "tool_result",
                                "tool_name": name,
                                "arguments": args,
                                "result": result_value,
                                "is_error": message.status == "error",
                            }
                        )
                elif isinstance(message, AIMessage):
                    # A message a middleware added without a model call (the turn cap's
                    # closing message) arrives whole, not as chunks, and is a plain
                    # AIMessage; dropping it would end the turn without saying why.
                    text = _extract_text(message.content)
                    if text:
                        text_parts.append(text)
                        await websocket.send_json({"type": "agent_delta", "text": text})
                if host._stop_requested:
                    break
        finally:
            await stream.aclose()
        _flush_accumulated()
        await _capture_segment_usage()
        return "".join(text_parts)

    async def announce_started_tools(self, update: Any, websocket: EventSink) -> None:
        """Tell the page which ungated calls are about to run. Gated ones are announced by
        the approval path instead, and only when nobody is asked: a call waiting for
        approval shows as its approval card."""
        if not isinstance(update, dict):
            return
        for node_update in update.values():
            if not isinstance(node_update, dict):
                continue
            for message in node_update.get("messages", []) or []:
                if not isinstance(message, AIMessage):
                    continue
                for call in message.tool_calls:
                    if call["name"] not in self._host._gated_tool_risks:
                        await self._host._send_tool_started(call["name"], call["args"], websocket)
