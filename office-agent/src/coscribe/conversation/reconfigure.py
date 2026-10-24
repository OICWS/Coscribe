"""Changing what a live conversation works with -- its environment, its folders and its enabled
skills -- between turns. Both rebuild the tools and the agent against the new setting and put the
session back exactly as it was if the rebuild fails, so a bad folder or skill never leaves a
half-changed session."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from pathlib import Path
from typing import Any, Protocol

from langchain_core.tools import BaseTool

from ..config import Settings
from ..runtime import Environments
from ..tools import SCHEDULED_THREAD_PREFIX, load_builtin_skills, load_skills
from .events import EventSink
from .turn_lock import TurnLock


class ReconfigureHost(Protocol):
    """What the folder and skill changes read and rewrite on the session they belong to."""

    settings: Settings
    thread_id: str
    model: Any
    lg_agent: Any
    workspace_root: Path
    extra_folders: list[Path]
    enabled_skill_names: set[str]
    skills_by_slug: dict[str, Any]
    _workspace_explicit: bool
    _instructions: str
    _base_tools: list[Callable[..., Any] | BaseTool]
    _gated_tool_risks: dict[str, str]
    _context_window: int | None
    _turn_lock: TurnLock

    def _build_agent(self) -> Any: ...

    def _build_lg_agent_with_risks(self) -> tuple[Any, dict[str, str]]: ...

    async def send_state(self, websocket: EventSink, *, on_connect: bool = False) -> None: ...


class SessionReconfigurer:
    def __init__(self, host: ReconfigureHost) -> None:
        self._host = host

    async def _wait_idle(self, websocket: EventSink, refusal: str) -> bool:
        # A short wait, not an immediate refusal: resume_after_reconnect holds the lock
        # for a moment right after every connect. Waiting for a real turn instead would
        # stall this socket's receive loop, and with it the approval that turn may be
        # waiting on. Polled rather than wait_for(acquire()): on 3.11 a timeout racing
        # the acquire can leave the lock held with nobody to release it.
        loop = asyncio.get_running_loop()
        deadline = loop.time() + 2
        while self._host._turn_lock.locked():
            if loop.time() >= deadline:
                await websocket.send_json({"type": "error", "message": refusal})
                return False
            await asyncio.sleep(0.05)
        return True

    async def set_folders(self, paths: list[str], websocket: EventSink) -> bool:
        """Replace the folders -- any time between turns. The first is the main one
        (relative paths resolve there); none means the app's default workspace. Returns
        whether it took effect, so the caller persists only what is in use."""
        if not await self._wait_idle(
            websocket, "Wait for the reply to finish, then change folders."
        ):
            return False
        async with self._host._turn_lock:
            return await self._apply_folders(paths, websocket)

    async def set_environment(self, env_id: str, websocket: EventSink) -> bool:
        """Moves the conversation to another environment and into its folders. Only between
        turns: a running turn keeps the environment it started with."""
        host = self._host
        environments = Environments(host.settings.state_dir)
        env = environments.get(env_id)
        if env is None:
            await websocket.send_json({"type": "error", "message": "That environment is gone."})
            return False
        refusal = "Wait for the reply to finish, then switch environments."
        if not await self._wait_idle(websocket, refusal):
            return False
        async with host._turn_lock:
            previous = environments.environment_of(host.thread_id)
            environments.assign(host.thread_id, env_id)
            if await self._apply_folders(env["folders"], websocket):
                return True
            environments.assign(host.thread_id, previous)
            return False

    async def add_folder(self, path: str, websocket: EventSink) -> bool:
        """One more folder, keeping the ones there are -- the default workspace stays the
        main one when none were chosen. Kept in the conversation's environment, except a
        scheduled run's, whose caller keeps it with the run."""
        host = self._host
        folder = Path(path).expanduser()
        current = [Path(host.workspace_root).resolve(), *host.extra_folders]
        if folder in current:
            return True
        paths = [str(p) for p in current] + [str(folder)]
        if not await self.set_folders(paths, websocket):
            return False
        if not host.thread_id.startswith(SCHEDULED_THREAD_PREFIX):
            Environments(host.settings.state_dir).add_folders(host.thread_id, paths, folder.name)
            await host.send_state(websocket)
        return True

    async def _apply_folders(self, paths: list[str], websocket: EventSink) -> bool:
        host = self._host
        chosen: list[Path] = []
        for raw in paths:
            folder = Path(raw).expanduser()
            if not folder.is_absolute() or not folder.is_dir():
                await websocket.send_json(
                    {"type": "error", "message": f"{raw!r} isn't an existing folder."}
                )
                return False
            if folder not in chosen:
                chosen.append(folder)
        previous = (
            host.workspace_root,
            host.extra_folders,
            host._workspace_explicit,
            host._instructions,
            host._base_tools,
            host.lg_agent,
            host._gated_tool_risks,
        )
        host._context_window = None
        try:
            host.workspace_root = chosen[0] if chosen else Path(host.settings.workspace_root)
            host.extra_folders = chosen[1:]
            host._workspace_explicit = bool(chosen)
            agent = host._build_agent()
            host._instructions = agent.instructions or ""
            host._base_tools = list(agent.tools)
            new_lg_agent, new_gated_tool_risks = host._build_lg_agent_with_risks()
        except Exception as exc:  # noqa: BLE001 -- a bad folder must not corrupt session state
            (
                host.workspace_root,
                host.extra_folders,
                host._workspace_explicit,
                host._instructions,
                host._base_tools,
                host.lg_agent,
                host._gated_tool_risks,
            ) = previous
            await websocket.send_json(
                {"type": "error", "message": f"Could not use those folders: {exc}"}
            )
            return False
        host.lg_agent = new_lg_agent
        host._gated_tool_risks = new_gated_tool_risks
        await host.send_state(websocket)
        return True

    async def set_enabled_skills(
        self, skill_names: set[str], websocket: EventSink, *, announce: bool = True
    ) -> None:
        """Replace the enabled skills, live, with no "once only" guard. Every call
        rebuilds the instructions and tools from scratch rather than adding skill text
        onto what a previous toggle left, so turning a skill off removes its listing."""
        host = self._host
        previous_instructions = host._instructions
        previous_base_tools = host._base_tools
        previous_lg_agent = host.lg_agent
        previous_gated_tool_risks = host._gated_tool_risks
        previous_enabled_skill_names = host.enabled_skill_names
        host.enabled_skill_names = set(skill_names)
        agent = host._build_agent()
        host._instructions = agent.instructions or ""
        host._base_tools = list(agent.tools)
        host._context_window = None
        try:
            new_lg_agent, new_gated_tool_risks = host._build_lg_agent_with_risks()
        except Exception as exc:  # noqa: BLE001 -- a bad rebuild must not corrupt session state
            host._instructions = previous_instructions
            host._base_tools = previous_base_tools
            host.lg_agent = previous_lg_agent
            host._gated_tool_risks = previous_gated_tool_risks
            host.enabled_skill_names = previous_enabled_skill_names
            host._context_window = None
            await websocket.send_json(
                {"type": "error", "message": f"Could not update skills: {exc}"}
            )
            return
        host.lg_agent = new_lg_agent
        host._gated_tool_risks = new_gated_tool_risks
        # Re-scanned so a skill /saveskill just wrote is usable as /<slug> in this same
        # session, and the lookup (unrestricted by enabled_skill_names) matches the disk.
        host.skills_by_slug = {
            skill.slug: skill
            for skill in load_builtin_skills() + load_skills(host.settings.skills_dir)
        }
        if announce:
            await host.send_state(websocket)
