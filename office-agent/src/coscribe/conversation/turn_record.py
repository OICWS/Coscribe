"""How each turn went, kept on this machine: one JSON line per turn with its model calls,
tokens, tools and outcome (decision 0045). It holds none of the conversation's words: no
message text, no tool arguments and no tool results, only the start of a tool's error text."""

from __future__ import annotations

import contextlib
import json
import time
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from langchain_core.messages import AIMessage, AIMessageChunk, ToolMessage

from ..runtime_lg import redact_secrets

# An error's first lines name what went wrong; the rest is usually the content it choked on.
_ERROR_CHARS = 300
# A turn that fails the same way fifty times says nothing more the fiftieth time.
_ERRORS_KEPT = 20
# About ten thousand turns. The file before it is kept, so a reader always has a recent run
# of turns, and nothing grows without a limit on a disk nobody looks at.
_MAX_BYTES = 5_000_000


def turns_path(state_dir: str | Path) -> Path:
    """One file for every conversation, as the audit log is: a turn's line is joined to its
    approval decisions by conversation id and time."""
    return Path(state_dir) / "turns.jsonl"


class TurnRecorder:
    """Counts one turn as it runs and writes its line when it ends."""

    def __init__(self, state_dir: str | Path, **head: Any) -> None:
        self._path = turns_path(state_dir)
        self._head = {"started": datetime.now(UTC).isoformat(), **head}
        self._clock = time.monotonic()
        self._model_calls = 0
        self._tokens = {"input_tokens": 0, "cached_tokens": 0, "output_tokens": 0}
        self._tools: dict[str, dict[str, int]] = {}
        self._tool_errors: list[dict[str, str]] = []
        self._error: BaseException | None = None

    def model_call(self) -> None:
        self._model_calls += 1
        # A call that answered after one that failed is a retry that worked.
        self._error = None

    def usage(self, usage: Any) -> None:
        """Add one streamed piece's `usage_metadata`; a provider that reports none adds nothing."""
        if not usage:
            return
        self._tokens["input_tokens"] += int(usage.get("input_tokens") or 0)
        self._tokens["output_tokens"] += int(usage.get("output_tokens") or 0)
        cached = (usage.get("input_token_details") or {}).get("cache_read")
        self._tokens["cached_tokens"] += int(cached or 0)

    def tool(self, name: str, *, is_error: bool, result: Any = None) -> None:
        count = self._tools.setdefault(name, {"calls": 0, "errors": 0})
        count["calls"] += 1
        if not is_error:
            return
        count["errors"] += 1
        if len(self._tool_errors) < _ERRORS_KEPT:
            text = result if isinstance(result, str) else json.dumps(result, default=str)
            self._tool_errors.append(
                {"tool": name, "text": str(redact_secrets(text[:_ERROR_CHARS]))}
            )

    def failed(self, error: BaseException) -> None:
        self._error = error

    def finish(self, *, stopped: bool) -> None:
        """Write the turn's line. Writing never fails the turn: a full disk or a locked file
        loses the line, not the reply."""
        if not self._model_calls and not self._tools and self._error is None:
            # A command such as /plan, or a stop before anything ran: nothing to learn from.
            return
        line = {
            **self._head,
            "seconds": round(time.monotonic() - self._clock, 2),
            "outcome": "error" if self._error else "stopped" if stopped else "completed",
            # The exception's type only: its text can quote the conversation.
            "error": type(self._error).__name__ if self._error else None,
            "model_calls": self._model_calls,
            **self._tokens,
            "tools": self._tools,
            "tool_errors": self._tool_errors,
        }
        with contextlib.suppress(OSError):
            self._path.parent.mkdir(parents=True, exist_ok=True)
            if self._path.is_file() and self._path.stat().st_size > _MAX_BYTES:
                self._path.replace(self._path.with_suffix(".1.jsonl"))
            with self._path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(line, ensure_ascii=False) + "\n")


async def observed(stream: Any, recorder: TurnRecorder | None) -> AsyncIterator[Any]:
    """A run's events, unchanged, counted into `recorder` as they pass."""
    try:
        async for mode, chunk in stream:
            if recorder is not None:
                _count(recorder, mode, chunk)
            yield mode, chunk
    except Exception as error:
        if recorder is not None:
            recorder.failed(error)
        raise


def _count(recorder: TurnRecorder, mode: str, chunk: Any) -> None:
    if mode == "updates":
        # The model node's update is one finished response; pieces of it arrive as "messages".
        update = chunk.get("model") if isinstance(chunk, dict) else None
        messages = update.get("messages") if isinstance(update, dict) else None
        for message in messages or []:
            if isinstance(message, AIMessage):
                recorder.model_call()
        return
    message = chunk[0]
    if isinstance(message, AIMessageChunk):
        recorder.usage(message.usage_metadata)
    elif isinstance(message, ToolMessage):
        recorder.tool(
            message.name or "", is_error=message.status == "error", result=message.content
        )
