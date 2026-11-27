"""Recognize the Markdown front matter that marks a Coscribe Doc."""

from __future__ import annotations

from typing import Any

MARKER_KEY = "coscribe"
MARKER_VALUE = "doc"


def doc_front_matter(lines: list[str]) -> tuple[dict[str, Any], int]:
    """The head's values and how many lines it takes; none when the file does not open with one."""
    if not lines or lines[0].strip().lstrip("﻿") != "---":
        return {}, 0
    for end in range(1, len(lines)):
        if lines[end].strip() == "---":
            import yaml

            try:
                head = yaml.safe_load("".join(lines[1:end])) or {}
            except yaml.YAMLError:
                return {}, 0
            return (head if isinstance(head, dict) else {}), end + 1
    return {}, 0


def is_doc(source: str) -> bool:
    meta, _ = doc_front_matter(source.splitlines(keepends=True))
    return str(meta.get(MARKER_KEY, "")).lower() == MARKER_VALUE
