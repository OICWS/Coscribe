"""Small helpers of a conversation's turns: reply and title text, the usage event, and the design
system a Slides conversation starts with."""

from __future__ import annotations

import re
import unicodedata
from typing import Any, Protocol

from langchain_core.messages.ai import UsageMetadata

from ..runtime_lg import (
    ACCEPT_EDITS_MODE_NOTE,
    AUTO_MODE_NOTE,
    NORMAL_MODE_NOTE,
    PLAN_MODE_NOTE,
)
from ..tools import DesignSystemStore, WorkspaceScope


class _Starting(Protocol):
    """What a conversation offers its first message: where it keeps state and its workspace."""

    settings: Any
    thread_id: str

    def workspace_scope(self) -> WorkspaceScope: ...


def design_system_for_start(
    session: _Starting, artifact: str | None, system_id: str | None
) -> dict[str, Any] | None:
    """The library system a Slides or Design conversation's first message names, kept as a copy
    for the conversation (its deck begins as that copy, whatever happens to the library later),
    its pictures copied into the workspace for the conversation to use. None for any other start,
    and for a system that is no longer in the library."""
    if artifact not in ("slides", "design") or not system_id:
        return None
    store = DesignSystemStore(session.settings.state_dir)
    system = store.choose_for_thread(session.thread_id, system_id)
    if system is not None and system.get("assets"):
        workspace = session.workspace_scope().root
        system = {**system, "assets": store.copy_assets(system_id, workspace)}
    return system


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


def turn_mode_note(plan_mode: bool, accept_edits: bool, auto_mode: bool) -> str:
    """The note in front of a turn's message that says how risky tool calls are handled."""
    if plan_mode:
        return PLAN_MODE_NOTE
    if accept_edits:
        return ACCEPT_EDITS_MODE_NOTE
    return AUTO_MODE_NOTE if auto_mode else NORMAL_MODE_NOTE


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
    "or falling back to a workaround. If the work needs a service no tool "
    "reaches (Notion, Jira, a CRM), call find_connector and offer what it "
    "finds with offer_connector rather than asking the user to set it up."
)


TITLE_INSTRUCTIONS = (
    "Name this conversation for a sidebar: at most 6 words (or 14 characters "
    "in Chinese or Japanese), in the language the user wrote in, saying what "
    "it's about. Reply with the title only -- no quotes, no ending punctuation."
)


# Characters of room in a sidebar row, counting a wide (Chinese, Japanese, Korean) one as two.
_TITLE_WIDTH = 40


# Some models (DeepSeek among them) sometimes answer the title request with reasoning or a
# tool call written out as text: a `<think>` block, a `<tool_call>` tag, or their own
# `<｜tool▁calls▁begin｜>` token, with the call's JSON after it. None of that is a title.
_REASONING = re.compile(r"<(think|thinking|reasoning)>.*?(</\1>|$)", re.IGNORECASE | re.DOTALL)
_TOOL_CALL = re.compile(
    r"<\s*/?\s*(tool_calls?|function_calls?|invoke)\b|<[|｜][^>]*tool", re.IGNORECASE
)
_TAG = re.compile(r"<[|｜][^>]*[|｜]>|</?[A-Za-z][\w:-]*/?>")


def clean_title(text: str) -> str:
    """The model's reply as a sidebar title, or "" when it holds no title, so that the first message
    stays the label and the end of the first turn asks again."""
    text = _REASONING.sub("", text)
    call = _TOOL_CALL.search(text)
    if call:
        text = text[: call.start()]
    lines = [line for line in (_TAG.sub("", line).strip() for line in text.splitlines()) if line]
    title = " ".join(lines[0].split()) if lines else ""
    title = title.strip("\"'“”「」《》*#。.").strip()
    if title.startswith(("{", "[")):
        return ""
    return _fit_title(title)


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
