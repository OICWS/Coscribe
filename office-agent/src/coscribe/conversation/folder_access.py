"""A folder outside the workspace, asked for from the chat (decision 0048).

The model calls `request_folder_access` after a file tool refused a path; the person answers on a
card. "Allow" adds the folder to Settings' Allowed folders and to the conversation's workspace,
the only one that uses it until another picks it (decision 0053), and "Only this chat" keeps it
to the conversation (`Environments.allow_for_thread`). Either way the
conversation's tools are built again before the turn goes on, so the model's next call reaches it.
"""

from __future__ import annotations

import uuid
from asyncio import Future, get_running_loop, to_thread
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from dotenv import dotenv_values, set_key

from ..config import Settings
from ..runtime import Environments
from ..runtime_lg import AuditLog, record_decision
from .events import EventSink

# Where the server and the Folder access page read Settings from (`config.Settings`).
ENV_FILE = Path(".env")

ALLOW = "allow"
THIS_CHAT = "chat"
IN_WORKSPACE = "workspace"
DENIED = "deny"

FOLDER_ACCESS = Environments.ACCESS

# Settings' Allowed folders, as the Folder access page writes them: a deletable folder is
# listed as writable too.
_ENV_KEYS = {
    "read": ("COSCRIBE_EXTRA_READABLE_DIRS",),
    "read-write": ("COSCRIBE_EXTRA_WRITABLE_DIRS",),
    "read-write-delete": ("COSCRIBE_EXTRA_WRITABLE_DIRS", "COSCRIBE_EXTRA_DELETABLE_DIRS"),
}
_FIELDS = {
    "COSCRIBE_EXTRA_READABLE_DIRS": "extra_readable_dirs",
    "COSCRIBE_EXTRA_WRITABLE_DIRS": "extra_writable_dirs",
    "COSCRIBE_EXTRA_DELETABLE_DIRS": "extra_deletable_dirs",
}


def _under(path: Path, folder: Path) -> bool:
    return path == folder or folder in path.parents


def checked_folder(raw: str) -> tuple[Path | None, str]:
    """The folder to offer, or why it isn't offered: one that exists and isn't too broad
    (`Environments.too_broad`)."""
    folder = Path(raw.strip()).expanduser()
    if not raw.strip() or not folder.is_absolute():
        return None, f"{raw!r} isn't an absolute folder path. Ask again with the full path."
    folder = folder.resolve()
    if not folder.is_dir():
        return None, f"{folder} isn't an existing folder."
    if Environments.too_broad(folder):
        return None, (
            f"{folder} is a whole drive, the home folder or holds it, which isn't offered. Ask "
            "for the folder that holds the files you need."
        )
    if "," in str(folder):
        # Settings keeps Allowed folders as one comma-separated value.
        return None, f"{folder} has a comma in its path, which Allowed folders can't hold."
    return folder, ""


def current_access(
    settings: Settings, thread_folders: dict[str, str], used: list[Path], folder: Path
) -> str | None:
    """How far the folder is already allowed: by an Allowed folder the workspace uses, or for
    this conversation only."""
    best: str | None = None
    places = [
        *((f, access) for f in used if (access := settings.allowed_access(f)) is not None),
        *((Path(f), access) for f, access in thread_folders.items()),
    ]
    for place, access in places:
        if _under(folder, place.expanduser().resolve()):
            if best is None or FOLDER_ACCESS.index(access) > FOLDER_ACCESS.index(best):
                best = access
    return best


def enough(have: str | None, wanted: str) -> bool:
    return have is not None and (wanted == "read" or have != "read")


def add_allowed_folder(
    settings: Settings, folder: Path, access: str, env_file: Path | None = None
) -> None:
    """Into Settings' Allowed folders: the .env the Folder access page edits, merged into what it
    holds now (the page writes it without updating the running server), and the running server's
    settings, so it holds without a restart."""
    env_file = env_file or ENV_FILE
    saved = dotenv_values(env_file) if env_file.is_file() else {}
    for key in _ENV_KEYS[access]:
        field = _FIELDS[key]
        listed = [Path(p.strip()) for p in (saved.get(key) or "").split(",") if p.strip()]
        running: list[Path] = list(getattr(settings, field))
        for current in (listed, running):
            if folder not in current:
                current.append(folder)
        setattr(settings, field, running)
        set_key(str(env_file), key, ", ".join(str(p) for p in listed), quote_mode="never")


def parse_answer(answer: Any) -> tuple[str, str]:
    """(what the person chose, the access) from the card's `answer`; anything else (a closed
    card, a stop, a reply typed in the chat) counts as not allowed."""
    if not isinstance(answer, str):
        return DENIED, ""
    choice, _, access = answer.partition(":")
    if choice in (ALLOW, THIS_CHAT) and access in FOLDER_ACCESS:
        return choice, access
    if choice == IN_WORKSPACE:
        return IN_WORKSPACE, ""
    return DENIED, ""


def result_message(choice: str, folder: Path, access: str, answer: Any, wanted: str) -> str:
    if choice in (ALLOW, THIS_CHAT):
        where = "this workspace" if choice == ALLOW else "this conversation only"
        if not enough(access, wanted):
            return (
                f"The user allowed {folder} for reading only ({where}), not writing. Read what "
                "you need there; save anything new in the workspace, and say where."
            )
        return f"The user allowed {folder} ({access}) for {where}. Call the refused tool again."
    if choice == IN_WORKSPACE:
        return (
            f"The user wants it saved in the workspace instead of {folder}. Save it there, and "
            "say where."
        )
    if isinstance(answer, dict) and isinstance(answer.get("reply"), str):
        return (
            f"The user didn't allow {folder} and wrote this instead; do what they ask:\n"
            f"{answer['reply']}"
        )
    if isinstance(answer, str) and answer.startswith("(Stopped"):
        return answer
    return f"The user didn't allow {folder}. Don't ask for it again; go on without it."


async def decide_folder_request(
    host: Any,
    args: dict[str, Any],
    websocket: EventSink,
    ask: Callable[[Any, dict[str, Any]], Awaitable[None]],
    open_prompts: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """The card for request_folder_access. The tools are built again after an allow, before the
    turn resumes, so the call the model repeats reaches the folder. The answer is audited like
    an approval, since Allow widens the workspace's later conversations."""
    folder, problem = checked_folder(str(args.get("folder", "")))
    if folder is None:
        return {"type": "respond", "message": problem}
    environments = Environments(host.settings.state_dir)
    wanted = "read-write" if args.get("access") == "write" else "read"
    used = list(host.extra_folders)
    have = current_access(host.settings, environments.thread_folders(host.thread_id), used, folder)
    if enough(have, wanted):
        # Allowed meanwhile, in Settings or on another conversation's card.
        failed = host._reconfigurer.refresh_folder_tools()
        message = failed or f"{folder} is allowed. Call the tool again."
        return {"type": "respond", "message": message}
    request_id = uuid.uuid4().hex
    future: Future[Any] = get_running_loop().create_future()
    host._pending_questions[request_id] = future
    event = {
        "type": "folder_access_required",
        "id": request_id,
        "folder": str(folder),
        "access": "read" if wanted == "read" else "write",
        "reason": str(args.get("reason", "")),
    }
    await ask(websocket, event)
    try:
        answer = await future
    finally:
        host._pending_questions.pop(request_id, None)
        open_prompts.pop(request_id, None)
    choice, access = parse_answer(answer)
    if choice == ALLOW:
        await to_thread(add_allowed_folder, host.settings, folder, access)
        main = str(host.workspace_root)
        await to_thread(environments.use_folder, host.thread_id, str(folder), main)
        if folder not in [Path(f) for f in host.extra_folders]:
            host.extra_folders = [*host.extra_folders, folder]
    elif choice == THIS_CHAT:
        await to_thread(environments.allow_for_thread, host.thread_id, str(folder), access)
    message = result_message(choice, folder, access, answer, wanted)
    if choice in (ALLOW, THIS_CHAT):
        message = host._reconfigurer.refresh_folder_tools() or message
    record_decision(
        AuditLog(host.settings.state_dir),
        thread_id=host.thread_id,
        tool_name="request_folder_access",
        arguments=args,
        decision="approve" if choice in (ALLOW, THIS_CHAT) else "reject",
        reason="human",
        detail=f"{choice}:{access}" if access else choice,
    )
    return {"type": "respond", "message": message}
