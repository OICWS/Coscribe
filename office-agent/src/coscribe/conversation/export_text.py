"""A conversation as one Markdown file a person can send along with a bug report: what was said, and
every tool call with its arguments and result, long ones shortened."""

from __future__ import annotations

import json
from typing import Any

_LIMIT = 1500


def _shortened(value: Any) -> str:
    text = (
        value
        if isinstance(value, str)
        else json.dumps(value, ensure_ascii=False, indent=2, default=str)
    )
    if len(text) <= _LIMIT:
        return text
    return f"{text[:_LIMIT]}\n... [{len(text) - _LIMIT} more characters left out]"


def conversation_markdown(thread_id: str, entries: list[dict[str, Any]]) -> str:
    """The replayed history (`serialize_history_for_ws_lg`) as Markdown."""
    parts = [
        f"# Conversation {thread_id}",
        f"Exported from Coscribe. Tool arguments and results are shortened to {_LIMIT} characters.",
    ]
    for entry in entries:
        kind = entry.get("kind")
        if kind in ("user", "agent"):
            speaker = "You" if kind == "user" else "Coscribe"
            parts.append(f"## {speaker}\n\n{entry.get('text', '')}")
        elif kind == "tool":
            failed = " (failed)" if entry.get("is_error") else ""
            lines = [f"### Tool: {entry.get('tool_name', '?')}{failed}"]
            lines.append(f"Arguments:\n```json\n{_shortened(entry.get('arguments', {}))}\n```")
            if entry.get("result") is not None:
                lines.append(f"Result:\n```\n{_shortened(entry['result'])}\n```")
            parts.append("\n\n".join(lines))
    return "\n\n".join(parts) + "\n"
