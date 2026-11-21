"""Side chat: a question about a conversation, answered beside it. The answer reads the
conversation as it is now and adds nothing to it, so it is never checkpointed, takes no turn lock
and runs while a turn does. It has no tools: the conversation's model answers from the transcript
alone."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langgraph.constants import TAG_NOSTREAM

from ..runtime_lg import extract_text

# The transcript keeps its newest part under this many characters: a side question is nearly
# always about what just happened, and the whole of a long conversation would not fit a model.
TRANSCRIPT_CHARS = 120_000
MAX_SIDE_MESSAGES = 40

SIDE_INSTRUCTIONS = (
    "You are Coscribe, answering a side question about the conversation below between a person "
    "and Coscribe, an assistant for office work. The person asks it in a side panel while the "
    "conversation goes on; nothing here is added to the conversation. You cannot use any tool, "
    "open a file or act: answer only from the transcript, and say so plainly when it does not "
    "hold the answer. Be brief, and answer in the language of the question.\n\n"
    "<conversation>\n{transcript}\n</conversation>"
)


def recent_part(transcript: str, limit: int = TRANSCRIPT_CHARS) -> str:
    """The end of the transcript, from a heading on, when the whole is over `limit`."""
    if len(transcript) <= limit:
        return transcript
    tail = transcript[-limit:]
    start = tail.find("\n## ")
    return "[Earlier messages left out]\n" + (tail[start + 1 :] if start >= 0 else tail)


def side_prompt(transcript: str, messages: Sequence[Mapping[str, str]]) -> list[BaseMessage]:
    prompt: list[BaseMessage] = [
        SystemMessage(content=SIDE_INSTRUCTIONS.format(transcript=recent_part(transcript)))
    ]
    for message in messages[-MAX_SIDE_MESSAGES:]:
        cls = HumanMessage if message["role"] == "user" else AIMessage
        prompt.append(cls(content=message["text"]))
    return prompt


async def answer_side_question(
    model: Any, transcript: str, messages: Sequence[Mapping[str, str]]
) -> str:
    """`messages` is the side chat so far (`role` "user" or "assistant", and `text`), ending
    with the person's question."""
    reply = await model.ainvoke(side_prompt(transcript, messages), config={"tags": [TAG_NOSTREAM]})
    return extract_text(reply.content).strip()
