"""The next message a person is likely to send, offered in the message box after a reply."""

from __future__ import annotations

import contextlib
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.constants import TAG_NOSTREAM

from ..runtime_lg import extract_text
from .events import EventSink

SUGGESTION_INSTRUCTIONS = (
    "You predict what the user will type next in a conversation with an assistant. "
    "Write the single most likely next message, as the user would write it: short (under "
    "15 words), in the language the user has been writing in, a natural follow-up or a "
    "go-ahead to the assistant's offer. Never answer for the assistant or explain. If the "
    "conversation is finished or nothing is clearly likely, reply with NONE. Reply with "
    "the message only -- no quotes."
)

MAX_SUGGESTION_CHARS = 120


def clean_suggestion(text: str) -> str:
    """The first line of the model's answer, or "" when it gave none worth offering."""
    lines = text.strip().splitlines()
    line = " ".join(lines[0].split()).strip("\"'“”「」《》") if lines else ""
    if not line or line.rstrip(".。").upper() == "NONE" or len(line) > MAX_SUGGESTION_CHARS:
        return ""
    return line


async def offer_next_prompt(
    model: Any, websocket: EventSink, user_text: str, reply_text: str
) -> None:
    """One short model call outside the agent graph, so the agent's tools and prompt stay as
    they are. A failure, or a tab that went away, only means no suggestion."""
    with contextlib.suppress(Exception):
        reply = await model.ainvoke(
            [
                SystemMessage(content=SUGGESTION_INSTRUCTIONS),
                HumanMessage(content=f"User: {user_text[:1500]}\n\nAssistant: {reply_text[:2500]}"),
            ],
            config={"tags": [TAG_NOSTREAM]},
        )
        suggestion = clean_suggestion(extract_text(reply.content))
        if suggestion:
            await websocket.send_json({"type": "prompt_suggestion", "text": suggestion})
