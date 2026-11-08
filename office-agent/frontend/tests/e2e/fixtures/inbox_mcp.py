"""A connector for the e2e specs: an inbox kept in the JSON file INBOX_FILE names, so a spec adds
a message by writing the file. One tool only reads (marked so); one changes the inbox (not
marked), as a real mail connector's would."""

import json
import os
from pathlib import Path

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

mcp = FastMCP("inbox")
INBOX = Path(os.environ["INBOX_FILE"])


def _messages() -> list[dict]:
    return json.loads(INBOX.read_text(encoding="utf-8")) if INBOX.exists() else []


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
def search_messages(label: str = "") -> dict:
    """Find the messages with a label, newest first."""
    found = [m for m in _messages() if not label or label in m.get("labels", [])]
    return {"messages": found[::-1]}


@mcp.tool()
def archive_message(message_id: str) -> str:
    """Archive a message."""
    INBOX.write_text(
        json.dumps([m for m in _messages() if m["id"] != message_id]), encoding="utf-8"
    )
    return "archived"


if __name__ == "__main__":
    mcp.run(transport="stdio")
