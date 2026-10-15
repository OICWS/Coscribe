"""Small pure helpers of a conversation's turns: reply and title text, the usage event."""

from __future__ import annotations

import unicodedata
from typing import Any

from langchain_core.messages.ai import UsageMetadata


def format_reply(text: str) -> str:
    if not text.strip():
        return "[no reply -- the model ended its turn without responding; try rephrasing]"
    return text


def build_instructions(agent_instructions: str | None, *, defer_tools: bool) -> str:
    """Appends _SEARCH_TOOLS_NOTE (only when some tools are actually left
    for search_tools to find) to whatever build_coordinator_agent
    assembled. Called where the agent is built and where its context is
    measured, from the same _tool_binding answer, so the note and the
    tool can't disagree."""
    notes: list[str] = []
    if defer_tools:
        notes.append(_SEARCH_TOOLS_NOTE)
    if not agent_instructions:
        return "\n\n".join(notes)
    return "\n\n".join([agent_instructions, *notes])


def usage_event(usage: UsageMetadata) -> dict[str, Any]:
    """Build the "usage" WS event from a response's UsageMetadata,
    including prompt-cache stats when the provider reports them --
    real, user-reported gap: the token counter only ever showed
    total_tokens, with no way to tell whether prompt caching was
    actually reducing anything or a long, tool-heavy conversation was
    genuinely just that large. `input_token_details.cache_read` is
    langchain-core's own standard field for "how many of this call's
    input tokens were served from cache" -- populated for Anthropic
    (this project's own explicit cache_control breakpoints) *and*,
    unprompted by any coscribe code, for any OpenAI-compatible provider
    too (langchain_openai maps the raw API's own `prompt_tokens_details.
    cached_tokens` into this same field -- confirmed by reading its
    source directly). GLM specifically documents "implicit caching":
    automatic, no cache_control equivalent needed, so this field simply
    starts appearing once a call's prompt prefix repeats one already
    seen. Omitted (not sent as 0) when the provider didn't report it at
    all, so the frontend can distinguish "no cache activity reported"
    from "genuinely zero tokens were cached this call" -- the two read
    very differently to a user trying to tell whether caching is
    working at all. cache_hit_rate is computed here, not on the
    frontend, so every caller (there are three) gets the identical
    definition (cache_read / input_tokens, Codex CLI's own metric,
    chosen over total_tokens as the denominator since output tokens are
    never cacheable and would understate the real hit rate)."""
    event: dict[str, Any] = {"type": "usage", "total_tokens": usage["total_tokens"]}
    cache_read = usage.get("input_token_details", {}).get("cache_read")
    input_tokens = usage.get("input_tokens")
    if cache_read is not None and input_tokens:
        event["cache_read_tokens"] = cache_read
        event["input_tokens"] = input_tokens
        event["cache_hit_rate"] = cache_read / input_tokens
    return event


# Only appended when Settings.defer_tools is on (see build_instructions
# below) -- the model has no other way to learn search_tools exists or
# when to reach for it, since most tools are hidden from its own tool
# list by default in that mode (see runtime_lg/tool_deferral.py).
_SEARCH_TOOLS_NOTE = (
    "Most tools beyond the basics aren't in your tool list -- this keeps "
    "this conversation's context small. If what you need isn't there (a "
    "PPTX/XLSX edit tool, a background script, a scheduled-task tool, "
    'etc.), call search_tools(query) first -- e.g. search_tools("pptx '
    'chart") -- it returns each match with its parameters. Run one with '
    "use_tool(name, arguments). Don't assume something can't be done "
    "just because you don't see a tool for it; search before giving up "
    "or falling back to a workaround."
)


TITLE_INSTRUCTIONS = (
    "Name this conversation for a sidebar: at most 6 words (or 14 characters "
    "in Chinese or Japanese), in the language the user wrote in, saying what "
    "it's about. Reply with the title only -- no quotes, no ending punctuation."
)


# Characters of room in a sidebar row, counting a wide (Chinese, Japanese, Korean) one as two.
_TITLE_WIDTH = 40


def clean_title(text: str) -> str:
    title = " ".join(text.strip().splitlines()[0].split()) if text.strip() else ""
    return _fit_title(title.strip("\"'“”「」《》*#。.").strip())


def _fit_title(title: str) -> str:
    """The title cut to the sidebar's width, for a model that answers with a sentence
    although it was asked for a few words."""
    width = 0
    end = 0
    for char in title:
        width += 2 if unicodedata.east_asian_width(char) in ("W", "F") else 1
        if width > _TITLE_WIDTH:
            break
        end += 1
    if end == len(title):
        return title
    cut = title[:end]
    space = cut.rfind(" ")
    return (cut[:space] if space > len(cut) * 0.6 else cut).rstrip() + "…"
