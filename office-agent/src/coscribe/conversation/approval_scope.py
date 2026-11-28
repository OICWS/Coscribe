"""What "allow similar in this chat" covers for one call, and what Auto mode's reviewer is told
about where a command runs (decision 0062)."""

from __future__ import annotations

import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path, PureWindowsPath
from typing import Any

from langchain_core.messages import HumanMessage

from ..runtime import NetworkGuard
from ..runtime_lg import (
    CODE_APPROVAL_RISKS,
    Verdict,
    extract_text,
    recent_user_requests,
    review_action,
    strip_mode_note,
)
from ..tools import sandbox_codex, sandbox_mode
from ..workflows import AgentCall
from .wire import AskReason

_COMMAND_TOOLS = ("run_background_command",)
# A line that runs more than one program: its first word doesn't say what it does.
_CHAINED = re.compile(r"&&|\|\||[|;&\n`]|\$\(")

_WHERE: dict[str, str] = {
    "command_unsandboxed": (
        "This command line runs outside any sandbox, as the user: it can change any of their "
        "files and use the network."
    ),
    "command_online": (
        "This command line runs in the sandbox, which writes only the conversation's folders "
        "but reads most of the user's files, and its network is on."
    ),
}


def command_rule(state_dir: Path, thread_id: str) -> AskReason | None:
    """Outside the sandbox a command runs as the person; inside it, it still reads most of
    their files, which an online command could send out. Either way the person approves it
    outside Auto and Bypass mode (decisions 0022, 0062). The unelevated sandbox reads everything
    and keeps a command offline only by its environment, so it never counts as holding one."""
    if sandbox_codex(state_dir) is None or sandbox_mode(state_dir) != "elevated":
        return "command_unsandboxed"
    if NetworkGuard(state_dir, thread_id).scripts_online():
        return "command_online"
    return None


def reviewer_where(rule: AskReason | None) -> str:
    """What the reviewer is told about where a command runs, so it can weigh that."""
    return _WHERE.get(rule or "", "")


def _program(command: str) -> str | None:
    line = command.strip()
    if not line or _CHAINED.search(line):
        return None
    quote = line[0] if line[0] in "\"'" else None
    first = line[1:].split(quote, 1)[0] if quote else line.split()[0]
    name = PureWindowsPath(first).name.lower()
    for suffix in (".exe", ".cmd", ".bat", ".com"):
        name = name.removesuffix(suffix)
    return name or None


@dataclass(frozen=True)
class SimilarCall:
    """What a card's "allow similar" remembers for a call, and the words its button shows."""

    key: str
    allow_similar: str


def similar_call(name: str, args: dict[str, Any]) -> SimilarCall | None:
    """What "allow similar" covers for this call, or None where nothing narrower than the call
    itself can be named."""
    if name in CODE_APPROVAL_RISKS:
        return None
    if name in _COMMAND_TOOLS:
        program = _program(str(args.get("command", "")))
        if program is None:
            return None
        return SimilarCall(f"{name}:{program}", f"Allow {program} commands in this chat")
    return SimilarCall(name, f"Allow {name} in this chat")


def _folders(host: Any) -> list[str]:
    return [str(folder) for folder in (host.folders or [host.workspace_root])]


def step_reviewer(host: Any) -> Callable[[AgentCall, str], Awaitable[Verdict | None]]:
    """Auto mode's reviewer for a workflow's agent step, where what the person saved the step
    to do stands in for what they said (decision 0062)."""

    async def review(call: AgentCall, saved: str) -> Verdict | None:
        rule = command_rule(host.settings.state_dir, host.thread_id)
        return await review_action(
            host._assembly.side_model(),
            tool_name=call.tool,
            arguments=call.args,
            risk=call.risk,
            folders=_folders(host),
            user_requests=saved,
            where=reviewer_where(rule) if call.tool in _COMMAND_TOOLS else "",
        )

    return review


async def review_call(
    host: Any, name: str, args: dict[str, Any], delegated_task: str, where: str
) -> Verdict | None:
    """Auto mode's reviewer on one call, with what the person has said in this conversation."""
    state = await host.lg_agent.aget_state(host.config)
    messages = list(state.values.get("messages", [])) if state.values else []
    return await review_action(
        host._assembly.side_model(),
        tool_name=name,
        arguments=args,
        risk=host._gated_tool_risks.get(name, "WRITE_LOCAL"),
        folders=_folders(host),
        user_requests=recent_user_requests(
            [
                HumanMessage(strip_mode_note(extract_text(m.content)))
                for m in messages
                # A message from another conversation or a sub-agent's report is stored as a
                # human message but is not what the user said.
                if m.type == "human" and not m.additional_kwargs.get("notice")
            ]
        ),
        delegated_task=delegated_task,
        where=where,
    )
