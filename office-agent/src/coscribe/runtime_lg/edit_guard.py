"""A change to a Word, Excel or PowerPoint file is not made from a copy the person has since
edited in the app. The guard remembers what each such file looked like after the model last read
or wrote it; a write tool that finds it different now (the person edited it meanwhile, a turn is
long) answers with a tool result saying so instead of writing. The model reads again, which
brings in the person's edits, and repeats the change on that. Nothing here touches a tool's
schema or the prompt (decision 0001): the news arrives in a tool result."""

from __future__ import annotations

import hashlib
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any

from langchain.agents.middleware import AgentMiddleware
from langchain_core.messages import ToolMessage

from .tool_deferral import unwrap_use_tool_call

GUARDED_SUFFIXES = frozenset({".docx", ".pptx", ".xlsx"})


def _digest(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


class EditGuardMiddleware(AgentMiddleware):
    """`resolve` turns a tool's `path` argument into the file it names (and raises for one outside
    the workspace); `write_tools` are the names of the tools that change a file."""

    def __init__(self, resolve: Callable[[str], Path], write_tools: Iterable[str]) -> None:
        super().__init__()
        self._resolve = resolve
        self._writes = frozenset(write_tools)
        self._seen: dict[Path, str] = {}

    def _target(self, request: Any) -> tuple[str, Path | None, str]:
        call = request.tool_call
        name, args = unwrap_use_tool_call(call["name"], call["args"])
        given = args.get("path")
        if not isinstance(given, str) or Path(given).suffix.lower() not in GUARDED_SUFFIXES:
            return name, None, ""
        try:
            return name, self._resolve(given), given
        except (OSError, ValueError, PermissionError):
            return name, None, ""

    def _refusal(self, request: Any, given: str) -> ToolMessage:
        call = request.tool_call
        return ToolMessage(
            content=(
                f"{given} was changed in the app by the user after you last read it, so nothing "
                "was written. Read it again (it holds their edits), then make the change on "
                "what you read."
            ),
            tool_call_id=call["id"],
            name=call["name"],
            status="error",
        )

    def _stale(self, name: str, path: Path | None) -> bool:
        if path is None or name not in self._writes or path not in self._seen:
            return False
        now = _digest(path)
        return now is not None and now != self._seen[path]

    def _remember(self, path: Path | None, result: Any) -> None:
        if path is None or getattr(result, "status", None) == "error":
            return
        now = _digest(path)
        if now is not None:
            self._seen[path] = now

    def wrap_tool_call(self, request: Any, handler: Any) -> Any:
        name, path, given = self._target(request)
        if self._stale(name, path):
            return self._refusal(request, given)
        result = handler(request)
        self._remember(path, result)
        return result

    async def awrap_tool_call(self, request: Any, handler: Any) -> Any:
        name, path, given = self._target(request)
        if self._stale(name, path):
            return self._refusal(request, given)
        result = await handler(request)
        self._remember(path, result)
        return result
