"""Starting a background command line: in Codex's sandbox where it is set up, else as the user
(decision 0022)."""

from __future__ import annotations

import asyncio
import logging
import os
import sys
import threading
from collections import Counter
from pathlib import Path

from ...runtime import NetworkGuard
from ._private_folders import GrantFailed, private_folders
from .capabilities import Capabilities, CapabilityOff, require_capability
from .command_sandbox import ELEVATED, codex_profile, sandbox_codex, sandbox_mode, sandboxed_command

logger = logging.getLogger(__name__)

# Commands approved without the person because the sandbox was set up, per conversation; one that
# finds the sandbox gone when it starts is refused instead of running as the person.
_SANDBOX_ASSUMED: Counter[str] = Counter()
_lock = threading.Lock()


def expect_sandbox(thread_id: str) -> None:
    """The approval of `thread_id`'s next command counted on the sandbox (decision 0022)."""
    with _lock:
        _SANDBOX_ASSUMED[thread_id] += 1


def _took_sandbox_for_granted(thread_id: str) -> bool:
    with _lock:
        if _SANDBOX_ASSUMED[thread_id] <= 0:
            return False
        _SANDBOX_ASSUMED[thread_id] -= 1
        return True


async def start_command(
    state: Path,
    thread_id: str,
    root: Path,
    folders: dict[str, list[Path]],
    command: str,
    env: dict[str, str],
) -> asyncio.subprocess.Process:
    """`command` running in `root` with its output in stdout, once the person allowed commands;
    `folders` holds the conversation's "writable" and "readable" ones."""
    assumed = _took_sandbox_for_granted(thread_id)
    require_capability(state, "commands", thread_id)
    online = NetworkGuard(state, thread_id).scripts_online()
    hide = Capabilities(state).get()["commands_hide_private_folders"]
    programs = [Path(p) for p in env.get("PATH", "").split(os.pathsep) if p]
    try:
        sandboxed = await asyncio.to_thread(
            sandboxed_command,
            state,
            command,
            root,
            folders["writable"],
            folders["readable"],
            online,
            hidden=private_folders() if hide else [],
            programs=programs,
        )
    except GrantFailed as exc:
        raise CapabilityOff(
            f'{exc} Tell the person; they can turn off "Hide your private folders from '
            'commands" in Settings › Capabilities, or move the folder.'
        ) from exc
    if sandboxed is None and assumed:
        raise CapabilityOff(
            "The command sandbox was removed after this command was approved, so it did not "
            "run. Run it again to ask the person."
        )
    if sandboxed is not None:
        argv, sandbox_env = sandboxed
        return await asyncio.create_subprocess_exec(
            *argv,
            cwd=str(root),
            env=env | sandbox_env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
    return await asyncio.create_subprocess_shell(
        command,
        cwd=str(root),
        env=env,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        # Its own process group, so a kill reaches what the shell started.
        start_new_session=sys.platform != "win32",
    )


def code_commands_allowed(state: Path, thread_id: str) -> bool:
    """Whether the code module's commands may run for `thread_id`: commands are on for it and
    the full sandbox is set up. Asked again for each command, so one turned off or removed
    mid-task stops the next (issue #616)."""
    try:
        require_capability(state, "commands", thread_id)
    except CapabilityOff:
        return False
    return sandbox_codex(state) is not None and sandbox_mode(state) == ELEVATED


def code_command_profile(
    state: Path, thread_id: str, folder: Path, programs: list[Path]
) -> tuple[str, dict[str, str]] | None:
    """The Codex permission profile that holds the code module's commands to `folder`, as
    `start_command` holds a conversation's, with the variables they need; None when commands are
    off for this conversation, the sandbox isn't set up, or a folder couldn't be granted, and then
    the code module's commands stay refused (issue #616). Runs icacls: call it off the event
    loop."""
    if not code_commands_allowed(state, thread_id):
        return None
    online = NetworkGuard(state, thread_id).scripts_online()
    hide = Capabilities(state).get()["commands_hide_private_folders"]
    try:
        return codex_profile(
            state,
            [folder],
            [],
            online,
            hidden=private_folders() if hide else [],
            programs=programs,
        )
    except GrantFailed:
        logger.warning(
            "the code module's commands stay off: a folder couldn't be granted", exc_info=True
        )
        return None
