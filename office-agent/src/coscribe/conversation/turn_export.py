"""A failed turn written out as the start of an evaluation task, when the person asks for it
(decision 0051). The file holds the turn's line from `turns.jsonl` and, if the person writes
them, their own words on what they asked and what went wrong: never the conversation's words."""

from __future__ import annotations

import contextlib
import json
import os
import re
from pathlib import Path
from typing import Any

from .. import __version__
from ..runtime_lg import redact_secrets
from .turn_record import turns_path

FORMAT = "coscribe-failed-turn/1"
# The newest turns are the ones a person remembers well enough to describe.
_LISTED = 20
_WORDS_CHARS = 2000
# What leaves the machine is named here, field by field, so a field added to the record later
# stays on the machine until someone decides it may go.
_TURN_FIELDS = (
    "started",
    "kind",
    "model",
    "effort",
    "mode",
    "notice",
    "seconds",
    "outcome",
    "error",
    "model_calls",
    "input_tokens",
    "cached_tokens",
    "output_tokens",
    "tools",
)


def _lines(state_dir: str | Path) -> list[dict[str, Any]]:
    current = turns_path(state_dir)
    lines: list[dict[str, Any]] = []
    for path in (current.with_suffix(".1.jsonl"), current):
        with contextlib.suppress(OSError):
            for text in path.read_text(encoding="utf-8").splitlines():
                with contextlib.suppress(ValueError):
                    line = json.loads(text)
                    if isinstance(line, dict):
                        lines.append(line)
    return lines


def _failed(line: dict[str, Any]) -> bool:
    # A stopped turn is often the person's own sign that it was going wrong.
    if line.get("outcome") in ("error", "stopped"):
        return True
    tools = line.get("tools") or {}
    return any((count or {}).get("errors") for count in tools.values())


def failed_turns(state_dir: str | Path, thread_id: str) -> list[dict[str, Any]]:
    """The conversation's turns that ended in an error, were stopped or had a tool fail, newest
    first, each as it would be exported without the person's words."""
    turns = [
        line for line in _lines(state_dir) if line.get("thread_id") == thread_id and _failed(line)
    ]
    turns.sort(key=lambda line: str(line.get("started", "")), reverse=True)
    return [eval_candidate(line) for line in turns[:_LISTED]]


def find_turn(state_dir: str | Path, thread_id: str, started: str) -> dict[str, Any] | None:
    """The conversation's recorded turn that started at `started`, failed or not."""
    for line in _lines(state_dir):
        if line.get("thread_id") == thread_id and line.get("started") == started:
            return line
    return None


def _without_home(text: str) -> str:
    """A path under the person's home names them (C:\\Users\\<name>); `~` says as much about
    where a file was without saying who."""
    home = str(Path.home())
    flags = re.IGNORECASE if os.name == "nt" else 0
    for spelling in {home, home.replace("\\", "/")}:
        if len(spelling) > 1:
            text = re.sub(re.escape(spelling), "~", text, flags=flags)
    return text


def _clean(text: str, limit: int) -> str:
    return _without_home(str(redact_secrets(text.strip()[:limit])))


def eval_candidate(
    line: dict[str, Any], *, asked: str = "", went_wrong: str = ""
) -> dict[str, Any]:
    """The exported file: the turn's numbers and its tool errors, without the conversation's id,
    and the person's own words if they wrote any."""
    errors = [
        {"tool": str(error.get("tool", "")), "text": _clean(str(error.get("text", "")), 300)}
        for error in line.get("tool_errors") or []
        if isinstance(error, dict)
    ]
    return {
        "format": FORMAT,
        "coscribe": __version__,
        "turn": {name: line[name] for name in _TURN_FIELDS if name in line},
        "tool_errors": errors,
        "asked": _clean(asked, _WORDS_CHARS),
        "went_wrong": _clean(went_wrong, _WORDS_CHARS),
    }
