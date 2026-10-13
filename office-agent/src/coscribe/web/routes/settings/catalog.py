"""Slash commands and the tool list."""

from __future__ import annotations

import inspect
from typing import Any

from fastapi import (
    APIRouter,
)

from ....coordinator import build_coordinator_agent
from ....runtime.types import get_tool_metadata
from ....tools import (
    load_builtin_skills,
    load_skills,
)
from ....workflows import describe_params, tool_description
from ...state import AppState

FIXED_COMMANDS = [
    {"name": "plan", "description": "Toggle Plan Mode (read-only tools only)"},
    {"name": "accept-edits", "description": "Toggle Accept-Edits Mode (no approval prompts)"},
    {"name": "compact", "description": "Summarize this thread to reclaim context"},
    {"name": "clear", "description": "Wipe this thread's conversation history and start fresh"},
    {"name": "stop", "description": "Stop the current in-progress run"},
    {"name": "init", "description": "Explore the workspace and write OVERVIEW.md"},
    {
        "name": "saveworkflow",
        "description": "Draft a workflow from what this conversation did "
        "(usage: /saveworkflow [name])",
    },
    {
        "name": "saveskill",
        "description": "Save this conversation as a reusable Skill (usage: /saveskill <name>)",
    },
]


def router(state: AppState) -> APIRouter:
    router = APIRouter()
    settings = state.settings
    _session_extra_tools = state.session_extra_tools

    @router.get("/api/commands")
    async def get_commands() -> list[dict[str, str]]:
        commands = list(FIXED_COMMANDS)
        for skill in load_builtin_skills() + load_skills(settings.skills_dir):
            # skill.slug, not skill.name -- "name" here means "the literal
            # token typed after /", same as every FIXED_COMMANDS entry
            # above (e.g. "accept-edits", not a display label); a skill's
            # own display name can contain spaces ("Skill Creator") and
            # was never usable as that token to begin with -- see
            # conversation/session.py's skills_by_slug for the matching half.
            commands.append({"name": skill.slug, "description": skill.description})
        return commands

    @router.get("/api/tools")
    async def get_tools() -> dict[str, Any]:
        agent = build_coordinator_agent(settings, thread_id="__tools_probe__")
        tools = []
        # Connected connectors' tools can be workflow steps too.
        for connector_tool in _session_extra_tools():
            metadata = get_tool_metadata(connector_tool)
            if not (metadata.category or "").startswith("mcp:"):
                continue
            tools.append(
                {
                    "name": connector_tool.name,
                    "category": metadata.category,
                    "risk_category": metadata.risk_category,
                    "requires_approval": metadata.requires_approval,
                    "description": tool_description(connector_tool).split(". ")[0],
                    "params": describe_params(connector_tool),
                }
            )
        for tool in agent.tools:
            metadata = get_tool_metadata(tool)
            doc = inspect.getdoc(tool) or ""
            # The docstring's first sentence, which often wraps past its
            # first line.
            first_paragraph = " ".join(doc.split("\n\n", 1)[0].split())
            description = first_paragraph.split(". ", 1)[0].rstrip(".") + "." if doc else ""
            tools.append(
                {
                    "name": tool.__name__,
                    "category": metadata.category or "",
                    "risk_category": metadata.risk_category,
                    "requires_approval": metadata.requires_approval,
                    "description": description,
                    "params": describe_params(tool),
                }
            )
        return {"tools": tools}

    return router
