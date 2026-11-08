"""A connector tool's result as the value a workflow step saves: connectors return text
blocks, sometimes wrapped in markdown sections, and later steps need the value inside."""

from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any

from langchain_core.tools import ToolException
from pydantic import ValidationError

logger = logging.getLogger(__name__)

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


async def ask_connector(tool: Any, args: dict[str, Any], seconds: float) -> tuple[Any, str | None]:
    """A connector tool's answer as a value, or why it gave none. Only the connector's own error
    and a refusal of the arguments are shown as they are: they are what the person can fix, and
    any other exception's text is the app's internals, which stay in the log."""
    try:
        return connector_value(await asyncio.wait_for(tool.ainvoke(dict(args)), seconds)), None
    except TimeoutError:
        return None, "It didn't answer in time"
    except (ToolException, ValidationError) as exc:
        return None, str(exc)[:300]
    except Exception as exc:
        logger.warning("asking connector tool %s failed", getattr(tool, "name", "?"), exc_info=True)
        return None, f"It failed ({type(exc).__name__}); the app's log has the details"
