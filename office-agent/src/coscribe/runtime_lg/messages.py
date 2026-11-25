"""Small LangGraph-message-shape helpers shared between conversation/session.py
(a live turn's own streaming) and the curator prompts in runtime_lg/
(e.g. skill_authoring.py), kept here so runtime_lg modules can use them
without importing session.py (which already imports from runtime_lg).
"""

from __future__ import annotations

import json
import re
from collections.abc import Sequence
from datetime import datetime
from typing import Any

from langchain_core.messages import HumanMessage, ToolMessage

# The exact mode_note prefixes session.py's _handle_user_message_locked
# prepends to every turn's user text before it becomes a checkpointed
# HumanMessage (for the model's benefit, so it always knows the active
# mode) -- defined here, not duplicated as inline literals in session.py,
# so serialize_history_for_ws_lg below can reliably strip them back off:
# the *live* user bubble (appendBubble("user", text) in app.js, sent the
# moment the user hits Send) never includes this prefix, since it's added
# server-side afterward -- a history replay showing it verbatim would be a
# visible inconsistency between a message rendered live vs. rendered from
# history for the exact same turn.
PLAN_MODE_NOTE = (
    "[plan mode is ON: research with read-only tools and write a plan; nothing "
    "else will run. When the plan is ready, call exit_plan_mode(plan) -- the "
    "user approves it before any change is made] "
)
ACCEPT_EDITS_MODE_NOTE = (
    "[accept-edits mode is ON: file edits in your folders run without asking; "
    "running code and acting outside this computer still ask] "
)
AUTO_MODE_NOTE = (
    "[auto mode is ON: a reviewer model checks each risky action instead of the "
    "user; one it blocks comes back refused with the reason -- find another way, "
    "or ask the user to allow that specific action] "
)
NORMAL_MODE_NOTE = "[normal mode: risky tool calls ask for approval as usual] "
# Earlier wordings, still at the front of checkpointed messages.
_OLD_MODE_NOTES = (
    "[plan mode is ON: only read-only/task-tracking tools will run, everything else is blocked] ",
    "[accept-edits mode is ON: tool calls run without asking] ",
)
_MODE_NOTES = (
    PLAN_MODE_NOTE,
    ACCEPT_EDITS_MODE_NOTE,
    AUTO_MODE_NOTE,
    NORMAL_MODE_NOTE,
    *_OLD_MODE_NOTES,
)

# Also matches the older date-only note, which checkpointed history still
# carries.
_WEEKDAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
_DATE_NOTE_RE = re.compile(
    r"^Today's real date is \d{4}-\d{2}-\d{2}"
    r"(?: \([A-Za-z]+\); local time \d{2}:\d{2} \(UTC[+-]\d{2}:\d{2}\))?\.\s+"
)


def current_date_note() -> str:
    """Real-world grounding the model has no other way to get: its own
    sense of "now" is anchored to its training cutoff, which is
    frequently well in the past by the time it's actually running here.
    Live-reported symptom this fixes: asked to web_search for current
    news, the model assumed a stale date, got real (correctly dated)
    results back, and -- with no authoritative "today is actually X" to
    reconcile against -- concluded its *own* tool must be broken rather
    than that its internal date guess was wrong.

    Prepended per-turn by session.py's _handle_user_message_locked,
    alongside mode_note -- NOT baked into coordinator.py's INSTRUCTIONS
    (where an earlier version of this lived, computed once at
    build_coordinator_agent time and glued onto the very front of the
    system prompt). That placement put the one genuinely volatile string
    in this whole prompt ahead of the large, otherwise-frozen INSTRUCTIONS
    block -- the worst possible spot for it: it poisoned the entire
    prefix for any future Anthropic cache_control breakpoint, and, since
    this app is multi-provider, just as surely defeated Gemini's and
    OpenAI-compatible providers' *automatic* prefix-based caching too, no
    cache_control needed on their end for the damage to apply. Moving it
    into per-turn message content instead of the frozen system prompt
    fixes this for every provider at once -- there's nothing
    provider-specific to configure, since the underlying cache mechanism
    everywhere is the same byte-prefix match. Bonus fix, not just a
    caching one: the old once-per-thread computation also went stale for
    any conversation that ran past midnight; recomputing every turn keeps
    it accurate throughout.

    strip_mode_note below must stay in sync with this -- a checkpointed
    HumanMessage carries this prefix too, and history replay needs to
    strip it back off the same way it does mode_note's.

    Also carries the weekday, local time and UTC offset: the model has no
    other clock. The weekday is spelled out here, not with %A, which follows
    the OS locale and would stop _DATE_NOTE_RE from matching."""
    now = datetime.now().astimezone()
    offset = now.strftime("%z")
    offset = f"{offset[:3]}:{offset[3:]}" if offset else "+00:00"
    return (
        f"Today's real date is {now.strftime('%Y-%m-%d')} ({_WEEKDAYS[now.weekday()]}); "
        f"local time {now.strftime('%H:%M')} (UTC{offset}). "
    )


_ARTIFACTS = {
    "docs": (
        "a new Doc the app opens in its editor. Load the Docs skill, then write one .md file "
        "with write_file as it says, and say its name when it is done"
    ),
    "slides": (
        "a new presentation the app opens in its Slides panel. Build it from pages, as your "
        "instructions for new decks say"
    ),
    "design": (
        "a new design the app opens on its Design canvas. Load the Design skill, then write "
        "its artboards' pages and the .design.json canvas as the skill says"
    ),
    "dashboard": (
        "a new dashboard the app opens in its Dashboard panel: a page of their real data. Load "
        "the Dashboard skill, find the data it is to show (ask where it is if they did not say), "
        "and write the page and its datasets as the skill says"
    ),
    "design-system": (
        "a new design system for their library. Ask for what is missing (brand colors, fonts, "
        "tone, who it is for), read what they attached with the file and image tools (for a "
        ".pptx template, read_pptx_design gives its colors, fonts, text sizes and the pictures "
        "its master draws), say the system you propose in words, and when they agree save it "
        "with save_design_system (find it with search_tools), with the logos and icons they "
        "attached or the template holds as its assets"
    ),
}
# "Sheets" stays so a history saved before that kind was dropped still loses its note.
_ARTIFACT_NOTE_RE = re.compile(
    r"^\[The user is starting a (?:Docs|Slides|Sheets|Design-system|Design|Dashboard) artifact: "
    r"[^\]]*\] "
)


_OVERVIEW_LIMIT = 2000


def _inline(text: object) -> str:
    """One line with no `]`: the note is one bracketed sentence, and `strip_mode_note` ends it
    at the first one."""
    return " ".join(str(text).replace("]", ")").split())


def design_system_text(system: dict[str, Any]) -> str:
    """A library design system as the sentence the model reads: what to follow, and where it may
    not apply. It guides; the person may ask for anything else."""
    parts = [f'Follow their design system "{_inline(system.get("name", ""))}".']
    overview = _inline(system.get("overview", ""))[:_OVERVIEW_LIMIT]
    if overview:
        parts.append(f"Overview: {overview}.")
    colors = [
        f"{_inline(c.get('name', ''))} {_inline(c.get('value', ''))}"
        + (f" ({_inline(c['note'])})" if c.get("note") else "")
        for c in system.get("colors", [])
    ]
    if colors:
        parts.append(f"Colors: {'; '.join(colors)}.")
    typography = system.get("typography", {})
    if typography.get("fonts"):
        parts.append(f"Fonts: {', '.join(_inline(f) for f in typography['fonts'])}.")
    styles = [
        f"{_inline(s.get('name', ''))} {s.get('size')}px weight {s.get('weight')}"
        for s in typography.get("styles", [])
    ]
    if styles:
        parts.append(f"Text styles: {'; '.join(styles)}.")
    for label, key in (("Spacing", "spacing"), ("Corner radius", "radius")):
        rows = [
            f"{_inline(r.get('name', ''))} {_inline(r.get('value', ''))}"
            for r in system.get(key, [])
        ]
        if rows:
            parts.append(f"{label}: {'; '.join(rows)}.")
    pictures = [
        f"{_inline(a['path'])} ({_inline(a.get('kind', 'picture'))}"
        + (f", {a['width']}x{a['height']}" if a.get("width") and a.get("height") else "")
        + (f", {_inline(a['note'])}" if a.get("note") else "")
        + ")"
        for a in system.get("assets", [])
        if isinstance(a, dict) and a.get("path")
    ]
    if pictures:
        parts.append(
            f"Its pictures, copied into the workspace: {'; '.join(pictures)}. Use a logo where its "
            "note says, copied into the deck or canvas folder."
        )
    return " ".join(parts)


def artifact_note(kind: str | None, design_system: dict[str, Any] | None = None) -> str:
    """What the conversation's first message is to make, when it started from the Artifacts page;
    it goes with the message, never in the system prompt or a tool schema. A Slides or Design
    conversation started with a library design system carries it in the same sentence."""
    if kind not in _ARTIFACTS:
        return ""
    sentence = f"{_ARTIFACTS[kind]}."
    if kind in ("slides", "design") and design_system:
        sentence += f" {design_system_text(design_system)}"
    if kind == "design" and design_system:
        # A system's text sizes are set on the 1920-wide slide its form edits.
        sentence += (
            " Make its colors, fonts, spacing and radius the canvas's variables; its text sizes "
            "are for a 1920-wide slide, so scale them to each artboard."
        )
    return f"[The user is starting a {kind.capitalize()} artifact: {sentence}] "


_LANGUAGE_NOTE_RE = re.compile(r"^\[The user writes in [^:\]]+: [^\]]*\] ")


def language_note(text: str) -> str:
    """Names the user's language when it isn't one written in Latin letters.

    The system prompt asks for the user's language everywhere, but at the
    start of a conversation -- everything the model has seen so far is that
    English prompt, this English note's neighbours and English tool output
    -- models still narrate their steps in English and only answer in the
    user's language. A concrete note next to the message itself holds."""
    latin = len(re.findall(r"[A-Za-z]", text))
    kana = len(re.findall(r"[\u3040-\u30ff]", text))
    hangul = len(re.findall(r"[\uac00-\ud7af]", text))
    han = len(re.findall(r"[\u4e00-\u9fff]", text))
    if kana >= 2:
        name = "Japanese"
    elif hangul >= 2 and hangul * 2 >= latin:
        name = "Korean"
    elif han >= 2 and han * 2 >= latin:
        name = "Chinese"
    else:
        return ""
    return (
        f"[The user writes in {name}: write the short notes between your steps in "
        f"{name} too, not only the final reply.] "
    )


_CONTEXT_NOTE_RE = re.compile(
    r"^\[Conversation context\]\n(.*?)\n\[/Conversation context\]\n", re.DOTALL
)


def context_note(context: str) -> str:
    """The conversation's folders and global instructions, sent ahead of the
    user's text when they differ from what the conversation was last told
    (see coordinator.conversation_context)."""
    return f"[Conversation context]\n{context}\n[/Conversation context]\n"


def last_conversation_context(messages: Sequence[Any]) -> str | None:
    """The context the conversation was most recently told, or None if no
    message in it carries one (a new conversation, or one compacted since)."""
    for message in reversed(messages):
        if getattr(message, "type", None) != "human":
            continue
        match = _CONTEXT_NOTE_RE.search(_strip_turn_notes(extract_text(message.content)))
        if match:
            return match.group(1)
    return None


def _strip_turn_notes(text: str) -> str:
    text = _DATE_NOTE_RE.sub("", text, count=1)
    for note in _MODE_NOTES:
        if text.startswith(note):
            text = text[len(note) :]
            break
    return _LANGUAGE_NOTE_RE.sub("", _ARTIFACT_NOTE_RE.sub("", text, count=1), count=1)


_ATTACHED_FILES_RE = re.compile(
    r"\n*\(Attached files, now in the workspace: (?P<paths>.+)\)\s*$", re.DOTALL
)


def split_attached_files(text: str) -> tuple[str, list[str]]:
    """A user message's text without the note that names the files it came with, and those
    files' workspace paths. The note stays in what the model reads; the page shows the files as
    cards instead (the composer joins the paths with ", ")."""
    found = _ATTACHED_FILES_RE.search(text)
    if found is None:
        return text, []
    paths = [path for path in found.group("paths").split(", ") if path]
    return text[: found.start()], paths


_OPEN_QUESTION_NOTE_RE = re.compile(
    r"^\[Open question card\]\n.*?\n\[/Open question card\]\n", re.DOTALL
)


def strip_mode_note(text: str) -> str:
    text = text.removeprefix(STEER_NOTE)
    text = _CONTEXT_NOTE_RE.sub("", _strip_turn_notes(text), count=1)
    return _OPEN_QUESTION_NOTE_RE.sub("", text, count=1)


STEER_NOTE = (
    "[The user added this while you were working. Take it into account from "
    "here on; it doesn't replace the request you're working on.]\n"
)
_STEER_MARK = "coscribe_steer"


def steer_message(text: str, images: Sequence[str] = ()) -> HumanMessage:
    """A note the user sent mid-turn, read before the model's next step, with the pictures
    attached to it. Marked so the per-turn counts don't take it for a new request."""
    content: str | list[str | dict[str, Any]] = STEER_NOTE + text
    if images:
        content = [{"type": "text", "text": STEER_NOTE + text}]
        content.extend({"type": "image_url", "image_url": {"url": url}} for url in images)
    return HumanMessage(content=content, additional_kwargs={_STEER_MARK: True})


def is_steer(message: Any) -> bool:
    return bool((getattr(message, "additional_kwargs", None) or {}).get(_STEER_MARK))


_PLAN_CHECK_MARK = "coscribe_plan_check"


def plan_check_message(text: str) -> HumanMessage:
    """The plan sent back to the model when it stops with tasks open. Marked as a steer so the
    per-turn counts and the edit and rewind positions skip it, and as a notice so it is not
    taken for what the user asked; the chat doesn't show it."""
    marks = {_STEER_MARK: True, _PLAN_CHECK_MARK: True, "notice": True}
    return HumanMessage(content=text, additional_kwargs=marks)


def is_plan_check(message: Any) -> bool:
    return bool((getattr(message, "additional_kwargs", None) or {}).get(_PLAN_CHECK_MARK))


def starts_a_turn(message: Any) -> bool:
    """A user's request: not a note added mid-turn, and not an
    auto-compact summary (a HumanMessage too)."""
    return (
        getattr(message, "type", None) == "human"
        and not is_steer(message)
        and (getattr(message, "additional_kwargs", None) or {}).get("lc_source") != "summarization"
        and not extract_text(message.content).startswith(
            "[Earlier conversation compacted to save context.]"
        )
    )


def extract_text(content: Any) -> str:
    """A message's .content is a plain string for most providers, but a
    list of content blocks for Gemini's thinking models -- pull the text
    out either way."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(str(block.get("text") or ""))
            elif isinstance(block, str):
                parts.append(block)
        return "".join(parts)
    return ""


def extract_images(content: Any) -> list[str]:
    """A HumanMessage's own image_url content blocks (see conversation/session.py's
    _handle_user_message_locked, which appends `{"type": "image_url",
    "image_url": {"url": ...}}` per attached image) -- the data URLs
    themselves, in the order they were attached. Mirrors extract_text's
    same list-of-content-blocks walk, just pulling a different block
    type; a plain-string .content (every non-multimodal message) has no
    images by construction."""
    if not isinstance(content, list):
        return []
    urls = []
    for block in content:
        if isinstance(block, dict) and block.get("type") == "image_url":
            url = block.get("image_url", {}).get("url")
            if url:
                urls.append(url)
    return urls


def _is_image_block(block: Any) -> bool:
    return isinstance(block, dict) and block.get("type") in ("image_url", "image")


def tool_result_value(content: Any) -> Any:
    """ToolMessage.content is usually a JSON-serialized string of the
    tool's real return value -- decode it back so callers see the raw
    object, not a JSON string. Falls back to the raw string if it isn't
    JSON. A result of content blocks (text and pictures, as look_at_page
    returns) is read from its text, with the number of pictures: the
    tab, the history and the hooks get no image data."""
    if isinstance(content, list) and any(_is_image_block(b) for b in content):
        texts = [
            b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text"
        ]
        value = tool_result_value("\n".join(texts))
        pictures = sum(1 for b in content if _is_image_block(b))
        return (
            {**value, "pictures": pictures}
            if isinstance(value, dict)
            else {"text": value, "pictures": pictures}
        )
    if isinstance(content, str):
        try:
            return json.loads(content)
        except ValueError:
            return content
    return content


def pictures_as_user_message(messages: list[Any]) -> tuple[list[Any], bool]:
    """Pictures a tool returned, moved out of its result into a user message right after the
    results of that step. OpenAI-compatible APIs do not all take an image in a tool message, while
    a user's image works wherever images do. Deterministic, so the prompt cache holds."""
    out: list[Any] = []
    pending: list[Any] = []
    changed = False

    def flush() -> None:
        if pending:
            note = {
                "type": "text",
                "text": "The pictures the tool results above refer to, in order:",
            }
            out.append(HumanMessage(content=[note, *pending]))
            pending.clear()

    for message in messages:
        if not isinstance(message, ToolMessage):
            flush()
            out.append(message)
            continue
        content = message.content
        if isinstance(content, list) and any(_is_image_block(b) for b in content):
            changed = True
            pending.extend(b for b in content if _is_image_block(b))
            text = [b for b in content if not _is_image_block(b)]
            message = message.model_copy(update={"content": text or "(pictures below)"})
        out.append(message)
    flush()
    return out, changed


def _compaction_note(message: Any, first: bool) -> str | None:
    if message.type != "human":
        return None
    extra = getattr(message, "additional_kwargs", {})
    text = extract_text(message.content)
    legacy = first and text.startswith("[Earlier conversation compacted to save context.]")
    if extra.get("lc_source") != "summarization" and not legacy:
        return None
    if not (
        legacy
        or text.startswith("Here is a summary of the conversation to date:")
        or text.startswith("[Earlier conversation compacted to save context.]")
    ):
        return ""
    saved = extra.get("coscribe_compaction", {}).get("tokens_saved")
    suffix = f" · ~{saved:,} tokens saved" if saved is not None else ""
    return f"Context compacted{suffix}"


def _user_history_entry(message: Any, text: str) -> dict[str, Any] | None:
    images = extract_images(message.content)
    if (not text and not images) or is_plan_check(message):
        return None
    kind = "steer" if is_steer(message) else "user"
    shown, files = split_attached_files(strip_mode_note(text))
    entry: dict[str, Any] = {"kind": kind, "text": shown}
    if images:
        entry["images"] = images
    if files:
        entry["files"] = files
    sent_at = (getattr(message, "additional_kwargs", None) or {}).get("sent_at")
    if kind == "user" and isinstance(sent_at, str):
        entry["sent_at"] = sent_at
    return entry


def serialize_history_for_ws_lg(messages: list[Any]) -> list[dict[str, Any]]:
    """Replay visible conversation entries, folding tool results into their calls.

    Keep images, file references and error status; strip model-only notes. Compaction
    summaries become short notices, never user messages or expandable summary text.
    """
    results_by_id: dict[str, tuple[Any, bool]] = {}
    for message in messages:
        if message.type == "tool" and getattr(message, "tool_call_id", None):
            is_error = getattr(message, "status", "success") == "error"
            results_by_id[message.tool_call_id] = (tool_result_value(message.content), is_error)
    entries: list[dict[str, Any]] = []
    for message in messages:
        compacted = _compaction_note(message, message is messages[0])
        if compacted is not None:
            if compacted:
                entries.append({"kind": "system", "text": compacted})
            continue
        tool_calls = getattr(message, "tool_calls", None)
        if tool_calls:
            text = extract_text(message.content)
            if text:
                entries.append({"kind": "agent", "text": text})
            for call in tool_calls:
                if call["id"] not in results_by_id:
                    continue
                result, is_error = results_by_id[call["id"]]
                entries.append(
                    {
                        "kind": "tool",
                        "tool_name": call["name"],
                        "arguments": dict(call["args"]),
                        "result": result,
                        "is_error": is_error,
                    }
                )
            continue
        if message.type == "tool":
            continue  # already folded into its call's own entry above
        text = extract_text(message.content)
        if message.type == "human":
            entry = _user_history_entry(message, text)
            if entry is not None:
                entries.append(entry)
            continue
        if not text:
            continue
        entries.append({"kind": "agent", "text": text})
    return entries


def render_transcript_lg(messages: list[Any]) -> str:
    """LangGraph message-object equivalent of runtime/compaction.py's
    render_transcript (which works on dict-shaped OpenAI messages instead).
    Doesn't special-case/drop a system message the way that function does
    -- verified empirically that create_agent's checkpointed state never
    contains one in the first place (system_prompt is injected at call time
    only, not stored in the thread's message history)."""
    lines = []
    for message in messages:
        tool_calls = getattr(message, "tool_calls", None)
        if tool_calls:
            names = ", ".join(tc["name"] for tc in tool_calls)
            lines.append(f"{message.type}: (called {names})")
            continue
        text = extract_text(message.content)
        if text:
            lines.append(f"{message.type}: {text}")
    return "\n".join(lines)
