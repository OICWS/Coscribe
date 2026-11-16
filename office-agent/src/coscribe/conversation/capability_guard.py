"""Two switches of Settings › Capabilities, held here: "files" (coscribe's own tools create and
change files) and "artifacts" (it makes Docs, designs and dashboards, which exist to be opened in
the app). A tool stays in the agent's list either way, since the provider caches that list
(decision 0001); with its switch off the call is refused and the model reads why. The same
question is asked before a person is asked to approve the call, so nobody approves a write that
would then be refused.

What is not held: a script or a command writes what it likes inside its folders, and each has its
own switch. An artifact that already exists can still be changed."""

from __future__ import annotations

import dataclasses
import functools
import inspect
import re
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from ..runtime import Agent, ToolMetadata, get_tool_metadata
from ..tools import Capabilities, WorkspaceScope
from .dashboard import is_dashboard
from .design_canvas import is_canvas

_FILE_CATEGORIES = frozenset({"filesystem", "documents"})

_FILES_OFF = (
    "Creating and editing files is turned off on this computer (Settings › Capabilities), so "
    "nothing was written. Give the person what you would have written in the conversation, and "
    "tell them they can turn it on there."
)
_ARTIFACTS_OFF = (
    "Artifacts are turned off on this computer (Settings › Capabilities), so this {kind} was not "
    "made. Answer in the conversation instead; if the person asked for a file to keep, write a "
    "Word, Excel or PowerPoint file. Tell them they can turn artifacts on there."
)
_DOC_MARKER = re.compile(r"^coscribe:\s*doc\s*$", re.IGNORECASE | re.MULTILINE)


class TurnedOff(ValueError):
    """A tool was called whose switch is off in Settings › Capabilities; the model reads why."""


def writes_files(metadata: ToolMetadata) -> bool:
    return metadata.risk_category == "WRITE_LOCAL" and metadata.category in _FILE_CATEGORIES


def _front_matter(content: str) -> str:
    lines = content.splitlines()
    if not lines or lines[0].strip() != "---":
        return ""
    for end, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            return "\n".join(lines[1:end])
    return ""


def _artifact_kind(path: str, content: str) -> str | None:
    """What kind of artifact writing `content` to `path` would make, None for a plain file."""
    suffix = Path(path).suffix.lower()
    if is_canvas(path):
        return "design"
    if suffix == ".md" and _DOC_MARKER.search(_front_matter(content)):
        return "Doc"
    if suffix in (".html", ".htm") and is_dashboard(content.encode("utf-8", "replace")):
        return "dashboard"
    return None


def _exists(scope: Callable[[], WorkspaceScope], path: str) -> bool:
    try:
        return scope().resolve(path).is_file()
    except (OSError, ValueError, PermissionError):
        return False


def capability_refusal(
    state_dir: Path,
    name: str,
    metadata: ToolMetadata,
    args: Mapping[str, Any],
    scope: Callable[[], WorkspaceScope],
) -> str | None:
    """Why this call may not run, None when it may. `scope` gives the conversation's folders as
    they are now, to see whether a path is already a file: a change to an artifact made earlier
    goes through."""
    if not writes_files(metadata):
        return None
    allowed = Capabilities(state_dir).get()
    if not allowed["files"]:
        return _FILES_OFF
    if allowed["artifacts"] or name != "write_file":
        return None
    path, content = args.get("path"), args.get("content")
    if not isinstance(path, str) or not isinstance(content, str):
        return None
    kind = _artifact_kind(path, content)
    if kind is None or _exists(scope, path):
        return None
    return _ARTIFACTS_OFF.format(kind=kind)


def _held(tool: Callable[..., Any], check: Callable[[Mapping[str, Any]], None]) -> Any:
    signature = inspect.signature(tool)

    def arguments(args: tuple[Any, ...], kwargs: dict[str, Any]) -> Mapping[str, Any]:
        return signature.bind_partial(*args, **kwargs).arguments

    if inspect.iscoroutinefunction(tool):

        @functools.wraps(tool)
        async def held_async(*args: Any, **kwargs: Any) -> Any:
            check(arguments(args, kwargs))
            return await tool(*args, **kwargs)

        return held_async

    @functools.wraps(tool)
    def held(*args: Any, **kwargs: Any) -> Any:
        check(arguments(args, kwargs))
        return tool(*args, **kwargs)

    return held


def hold_to_capabilities(
    agent: Agent, state_dir: Path, scope: Callable[[], WorkspaceScope]
) -> Agent:
    """The agent with each file-writing tool refusing while its switch is off. A tool keeps its
    name, signature, docstring and metadata, so its schema is the same."""

    def guard(tool: Callable[..., Any]) -> Any:
        metadata = get_tool_metadata(tool)
        if not callable(tool) or not writes_files(metadata):
            return tool
        name = getattr(tool, "__name__", "")

        def check(args: Mapping[str, Any]) -> None:
            refusal = capability_refusal(state_dir, name, metadata, args, scope)
            if refusal is not None:
                raise TurnedOff(refusal)

        return _held(tool, check)

    return dataclasses.replace(agent, tools=[guard(tool) for tool in agent.tools])
