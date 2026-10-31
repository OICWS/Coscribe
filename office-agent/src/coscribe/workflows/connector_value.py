"""A connector tool's result as the value a workflow step saves: connectors return text
blocks, sometimes wrapped in markdown sections, and later steps need the value inside."""

from __future__ import annotations

import json
import re
from typing import Any

_SECTION_HEADING = re.compile(r"^### (.+?)\s*$", re.MULTILINE)


def _result_section(text: str) -> str | None:
    """The body of a `### Result` section, for connectors (Playwright's)
    that wrap a tool's value in markdown sections alongside the code they
    ran and the page state -- the value is what later steps need."""
    if not text.startswith("### "):
        return None
    headings = list(_SECTION_HEADING.finditer(text))
    for index, heading in enumerate(headings):
        if heading.group(1).strip().lower() == "result":
            end = headings[index + 1].start() if index + 1 < len(headings) else len(text)
            return text[heading.end() : end].strip()
    return None


def connector_value(result: Any) -> Any:
    """What a connector's tool returned, as a value: its text content
    blocks joined, its `### Result` section if it has one, and JSON
    decoded where the text is JSON."""
    if isinstance(result, tuple):  # (content, artifact)
        result = result[0]
    if isinstance(result, list) and all(
        isinstance(block, dict) and block.get("type") == "text" for block in result
    ):
        result = "\n".join(str(block.get("text", "")) for block in result)
    if isinstance(result, str):
        result = _result_section(result) or result
        try:
            return json.loads(result)
        except ValueError:
            return result
    return result
