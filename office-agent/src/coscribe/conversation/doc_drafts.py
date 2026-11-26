"""Transient Doc previews derived from the model's streamed file-tool arguments."""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Callable
from pathlib import Path
from time import monotonic
from typing import Any
from uuid import uuid4

from langchain_core.messages import AIMessageChunk
from langchain_core.utils.json import parse_partial_json

from ..runtime_lg import unwrap_use_tool_call
from ..tools import WorkspaceScope
from ..tools.office.doc import read_doc
from .events import EventSink

logger = logging.getLogger(__name__)

_MAX_SOURCE = 128_000
_DOC_TOOLS = {"write_file", "edit_file", "edit_file_batch"}
_FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})")


def _complete_field(raw: str, field: str) -> bool:
    # A partial old_text must never match and remove a shorter piece of a paragraph.
    match = re.search(rf'(?<!\\)"{field}"\s*:\s*', raw)
    if not match:
        return False
    try:
        _, end = json.JSONDecoder().raw_decode(raw, match.end())
    except ValueError:
        return False
    return bool(raw[end:].lstrip().startswith((",", "}")))


def _arguments(chunk: dict[str, Any]) -> tuple[str, dict[str, Any], str]:
    raw = chunk.get("args") or ""
    if len(raw) > 4 * _MAX_SOURCE:
        return "", {}, ""
    try:
        args = parse_partial_json(raw)
        if not isinstance(args, dict):
            return "", {}, ""
        if chunk.get("name") == "use_tool" and isinstance(args.get("arguments"), str):
            raw = args["arguments"]
            args["arguments"] = parse_partial_json(raw)
        name, args = unwrap_use_tool_call(chunk.get("name") or "", args)
        return name, args, raw
    except (ValueError, TypeError):
        return "", {}, ""


def _candidate(name: str, args: dict[str, Any], raw: str, base: str | None) -> str | None:
    if name == "write_file":
        value = args.get("content")
        if base is not None and args.get("overwrite") is False:
            return None
        return value if isinstance(value, str) else None
    if base is None:
        return None
    if name == "edit_file_batch":
        batch = args.get("edits")
        if not isinstance(batch, str):
            return None
        chunks = [part for part in batch.split("\n---\n") if part.strip()]
        pairs = zip(chunks[::2], chunks[1::2], strict=False)
        changed = False
        for before, after in pairs:
            if base.count(before) != 1:
                return None
            base = base.replace(before, after, 1)
            changed = True
        return base if changed else None
    old, new = args.get("old_text"), args.get("new_text")
    if not isinstance(old, str) or not old or not isinstance(new, str):
        return None
    if not old:
        return None
    count = base.count(old)
    if not _complete_field(raw, "old_text") or (
        count != 1 and not (count and args.get("replace_all") is True)
    ):
        return None
    return base.replace(old, new)


def _draft_blocks(source: str) -> list[dict[str, Any]]:
    blocks = read_doc(source).blocks
    result = []
    for block in blocks:
        if block.kind == "chart":
            lines = block.text.splitlines()
            opening = _FENCE.match(lines[0])
            closing = _FENCE.match(lines[-1])
            if not opening or not closing or len(lines) < 3 or len(closing[1]) < len(opening[1]):
                continue
        result.append({"index": block.index, "kind": block.kind, "text": block.text})
    return result


class DocDrafts:
    def __init__(self, websocket: EventSink) -> None:
        self._websocket = websocket
        self._active: dict[str, tuple[str, str]] = {}
        self._base: dict[str, tuple[Path, str | None]] = {}
        self._last: dict[str, str] = {}
        self._next_update = 0.0

    async def update(
        self,
        message: AIMessageChunk,
        scope: Callable[[], WorkspaceScope],
        *,
        force: bool = False,
    ) -> None:
        # `force` sends the arguments' last state: a chunk the throttle skipped is never resent,
        # and a gated call would otherwise wait for approval behind an incomplete draft.
        now = monotonic()
        if not message.tool_call_chunks or (now < self._next_update and not force):
            return
        self._next_update = now + 0.09
        for call in message.tool_call_chunks:
            call_id = call.get("id")
            name, args, raw = _arguments(dict(call))
            path = args.get("path")
            if not call_id or name not in _DOC_TOOLS or not isinstance(path, str):
                continue
            if not path.lower().endswith(".md") or not _complete_field(raw, "path"):
                continue
            try:
                await self._publish(call_id, name, scope(), path, args, raw)
            # A preview never ends the turn it shows: half-written arguments and Markdown fail
            # in many ways.
            except (OSError, ValueError, RuntimeError, LookupError, TypeError, AttributeError):
                logger.debug("Doc draft preview skipped", exc_info=True)

    async def _publish(
        self,
        call_id: str,
        name: str,
        scope: WorkspaceScope,
        path: str,
        args: dict[str, Any],
        raw: str,
    ) -> None:
        target = scope.resolve(path, write=True)
        if call_id not in self._base:
            base = None
            if target.is_file():
                if target.stat().st_size > _MAX_SOURCE:
                    return
                base = target.read_text(encoding="utf-8-sig")
            self._base[call_id] = (target, base)
        previous, base = self._base[call_id]
        if previous != target:
            return
        source = _candidate(name, args, raw, base)
        if source is None or len(source) > _MAX_SOURCE or source == self._last.get(call_id):
            return
        blocks = _draft_blocks(source.encode("utf-8", errors="replace").decode("utf-8"))
        shown_path = scope.relative(target) if target.is_relative_to(scope.root) else str(target)
        _, preview_id = self._active.get(call_id, (shown_path, uuid4().hex))
        self._active[call_id] = (shown_path, preview_id)
        self._last[call_id] = source
        await self._websocket.send_json(
            {
                "type": "doc_draft",
                "id": preview_id,
                "path": shown_path,
                "new": base is None,
                "blocks": blocks,
            }
        )

    async def finish(self, call_id: str, committed: bool = False) -> None:
        self._base.pop(call_id, None)
        self._last.pop(call_id, None)
        active = self._active.pop(call_id, None)
        if active is not None:
            path, preview_id = active
            await self._websocket.send_json(
                {
                    "type": "doc_draft_finished",
                    "id": preview_id,
                    "path": path,
                    "committed": committed,
                }
            )

    async def close(self) -> None:
        for call_id in list(self._active):
            await self.finish(call_id)
