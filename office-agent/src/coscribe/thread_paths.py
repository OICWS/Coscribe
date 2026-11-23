"""Paths belonging to one conversation under the application's state directory."""

from __future__ import annotations

import re
from pathlib import Path, PureWindowsPath
from urllib.parse import quote


class InvalidThreadId(ValueError):
    pass


def is_thread_id(value: str) -> bool:
    """Whether the ID can form a filename on the supported platforms."""
    return bool(
        value
        and not value.endswith((" ", "."))
        and not re.search(r'[\\/:*?"<>|\x00-\x1f]', value)
        and not PureWindowsPath(value).is_reserved()
    )


def validate_thread_id(thread_id: str) -> None:
    if not is_thread_id(thread_id):
        raise InvalidThreadId("Invalid conversation ID")


def thread_file(root: str | Path, thread_id: str, suffix: str, *, quoted: bool = False) -> Path:
    validate_thread_id(thread_id)
    name = quote(thread_id, safe="") if quoted else thread_id
    path = Path(root) / (name + suffix)
    if path.resolve().parent != Path(root).resolve():
        raise InvalidThreadId("Conversation file is outside its state directory")
    return path
