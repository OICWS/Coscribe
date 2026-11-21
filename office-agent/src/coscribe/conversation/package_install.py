"""A package a script needs, installed from the chat once the person says yes (decision 0057).

The model calls `install_package` after a script failed on a missing module; the person answers
on a card, and Install runs the same installer as Settings › Packages, into the same
environment. Only a plain name with at most one version reaches the card: pip and npm read a URL,
a path or an option in that place as something else to install or somewhere else to install
from, which the card's name would not show.
"""

from __future__ import annotations

import re
import uuid
from asyncio import Future, get_running_loop, to_thread
from typing import Any

from ..runtime_lg import AuditLog, record_decision
from ..tools import (
    install_node_package,
    install_python_package,
    list_node_packages,
    list_python_packages,
)
from .events import EventSink

INSTALL = "install"

_ENVIRONMENT = {"python": "coscribe's Python environment", "node": "coscribe's Node.js environment"}

# PEP 508 names, with extras, and one PEP 440 specifier at most.
_PYTHON_SPEC = re.compile(
    r"(?P<name>[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?)"
    r"(?:\[[A-Za-z0-9._-]+(?:,[A-Za-z0-9._-]+)*\])?"
    r"(?:(?P<op>===|==|~=|!=|>=|<=|>|<)(?P<version>[A-Za-z0-9.*+!_-]+))?"
)
# npm names (lowercase, optionally scoped) and one version or range after "@".
_NODE_SPEC = re.compile(
    r"(?P<name>(?:@[a-z0-9][a-z0-9._-]*/)?[a-z0-9][a-z0-9._-]*)"
    r"(?:@(?P<version>[A-Za-z0-9.^~*+_-]+))?"
)
_MAX_SPEC = 120
_MAX_ERROR = 1500


def parse_spec(runtime: str, package: str) -> tuple[str, str | None] | None:
    """(name, exact version or None) when `package` is one plain package for `runtime`."""
    pattern = {"python": _PYTHON_SPEC, "node": _NODE_SPEC}.get(runtime)
    if pattern is None or len(package) > _MAX_SPEC:
        return None
    match = pattern.fullmatch(package)
    if match is None:
        return None
    exact = runtime == "node" or match.group("op") in ("==", "===")
    return match.group("name"), (match.group("version") if exact else None)


def _normalized(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def installed_version(state_dir: Any, runtime: str, name: str) -> str | None:
    lister = list_python_packages if runtime == "python" else list_node_packages
    wanted = _normalized(name)
    for package in lister(state_dir):
        if _normalized(str(package.get("name", ""))) == wanted:
            return str(package.get("version", "")) or None
    return None


def _install(state_dir: Any, runtime: str, package: str, name: str) -> dict[str, Any]:
    installer = install_python_package if runtime == "python" else install_node_package
    try:
        outcome = installer(state_dir, package)
    except RuntimeError as exc:  # no Node.js on the machine, or the venv could not be built
        return {"installed": False, "error": str(exc)}
    if not outcome.get("success"):
        error = str(outcome.get("error") or "The installer failed without a message.")
        return {"installed": False, "error": error[-_MAX_ERROR:]}
    try:
        version = installed_version(state_dir, runtime, name)
    except RuntimeError:
        version = None
    return {"installed": True, "version": version}


async def decide_package_install(
    decider: Any, args: dict[str, Any], websocket: EventSink
) -> dict[str, Any]:
    """The card for install_package, asked through the conversation's `ApprovalDecider`, whose
    `declined_packages` holds what the person turned down there: that is answered without one."""
    host = decider._host
    declined: set[tuple[str, str]] = decider.declined_packages
    runtime = str(args.get("runtime", ""))
    package = str(args.get("package", "")).strip()
    parsed = parse_spec(runtime, package)
    if parsed is None:
        return {
            "type": "respond",
            "message": (
                f"{package!r} is not one package name for {runtime or 'a runtime'}. Ask for one "
                "package by its name, with at most a version (e.g. openpyxl, openpyxl==3.1.2, "
                "sharp@0.33.5); URLs, paths, options and several names are refused."
            ),
        }
    name, version = parsed
    if (runtime, _normalized(name)) in declined:
        return {
            "type": "respond",
            "message": (
                f"The user already declined installing {name} in this conversation. Don't ask "
                "again; do the work without it or tell them what it needs."
            ),
        }
    state_dir = host.settings.state_dir
    try:
        have = await to_thread(installed_version, state_dir, runtime, name)
    except RuntimeError:
        have = None
    if have is not None and (version is None or version == have):
        return {
            "type": "respond",
            "message": f"{name} {have} is already installed in {_ENVIRONMENT[runtime]}.",
        }

    request_id = uuid.uuid4().hex
    future: Future[Any] = get_running_loop().create_future()
    host._pending_questions[request_id] = future
    event = {
        "type": "package_install_required",
        "id": request_id,
        "runtime": runtime,
        "package": package,
        "name": name,
        "reason": str(args.get("reason", "")),
        "installed_version": have,
    }
    await decider._ask(websocket, event)
    try:
        answer = await future
    finally:
        host._pending_questions.pop(request_id, None)
        decider.open_prompts.pop(request_id, None)

    audit = AuditLog(state_dir)
    if answer != INSTALL:
        if not isinstance(answer, dict):
            declined.add((runtime, _normalized(name)))
        record_decision(
            audit,
            thread_id=host.thread_id,
            tool_name="install_package",
            arguments=args,
            decision="reject",
            reason="human",
        )
        return {"type": "respond", "message": _declined_message(name, answer)}

    outcome = await to_thread(_install, state_dir, runtime, package, name)
    await websocket.send_json({"type": "package_install_finished", "id": request_id, **outcome})
    record_decision(
        audit,
        thread_id=host.thread_id,
        tool_name="install_package",
        arguments=args,
        decision="approve",
        reason="human",
        detail="installed" if outcome["installed"] else "install failed",
    )
    if outcome["installed"]:
        installed = f"{name} {outcome['version']}" if outcome.get("version") else package
        return {
            "type": "respond",
            "message": f"Installed {installed} into {_ENVIRONMENT[runtime]}. Run the script again.",
        }
    return {
        "type": "respond",
        "message": (
            f"Installing {package} failed; the user has seen this error:\n{outcome['error']}\n"
            "Check the name; don't ask again for the same package unless the error says the "
            "problem was passing (a network failure)."
        ),
    }


def _declined_message(name: str, answer: Any) -> str:
    if isinstance(answer, dict) and isinstance(answer.get("reply"), str):
        return (
            f"The user didn't install {name} and wrote this instead; do what they ask:\n"
            f"{answer['reply']}"
        )
    if isinstance(answer, str) and answer.startswith("(Stopped"):
        return answer
    return (
        f"The user chose not to install {name}. Don't ask for it again in this conversation; "
        "do the work without it or tell them what it needs."
    )
