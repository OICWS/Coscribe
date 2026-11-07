"""Ready-made sub-agent roles, so a delegation doesn't depend on a role written on the spot.

Each role says what the sub-agent is told and which of the delegating conversation's tools it
gets when the call names none. Both roles change nothing: research only reads, check may also
run a script (approved as any other) to recompute a figure.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any, cast

from langchain_core.tools import BaseTool

from ..runtime import get_tool_metadata

DEFAULT_SUBAGENT_INSTRUCTIONS = (
    "You are doing one task delegated to you by another assistant. Do the "
    "task with your tools, then reply with a short, complete report of what "
    "you did and found -- that reply is all the other assistant will see."
)


@dataclass(frozen=True)
class SubAgentRole:
    instructions: str
    # The risk categories of the tools it gets; None for every tool.
    risks: frozenset[str] | None = None

    def tools(
        self, available: Iterable[Callable[..., Any] | BaseTool]
    ) -> list[Callable[..., Any] | BaseTool]:
        # Connector tools are tagged EXTERNAL (mcp.py), so a read-only role gets none of them.
        return [
            t
            for t in available
            if self.risks is None
            or get_tool_metadata(cast(Callable[..., Any], t)).risk_category in self.risks
        ]


SUBAGENT_KINDS = {
    "research": SubAgentRole(
        "You are a researcher doing one task delegated to you by another assistant. Find what "
        "the task asks in the files and on the web with your tools; change nothing. Reply with "
        "a short report: each finding with where it came from (a file path and page or sheet, "
        "or a URL), and what you looked for and did not find. Stop as soon as you have enough.",
        frozenset({"READ"}),
    ),
    "check": SubAgentRole(
        "You are a checker doing one task delegated to you by another assistant: confirm the "
        "figures and statements it gives you against their sources. Read the sources yourself, "
        "and recompute a figure with a script when reading can't settle it; change no file. "
        "Reply with one line per item: confirmed, wrong (with the right value and where it "
        "comes from), or can't tell (and why).",
        frozenset({"READ", "EXEC"}),
    ),
}

KIND_ARG_DOC = """
kind: a ready-made role; empty for none. "research" finds things in
    files and on the web and reports each with its source (read-only
    tools); several research runs on separate questions can go in one
    step. "check" confirms the figures and statements you give it
    against their sources (read-only tools and scripts). instructions
    and tool_names, when given, take the kind's place."""


def subagent_role(kind: str, instructions: str) -> SubAgentRole:
    """The role a delegation runs under: its own instructions over the kind's, the kind's over
    the default."""
    name = kind.strip()
    if name and name not in SUBAGENT_KINDS:
        raise ValueError(
            f"Unknown sub-agent kind {kind!r}; use one of: {', '.join(SUBAGENT_KINDS)}"
        )
    role = SUBAGENT_KINDS[name] if name else SubAgentRole(DEFAULT_SUBAGENT_INSTRUCTIONS)
    if instructions.strip():
        return SubAgentRole(instructions.strip(), role.risks)
    return role
