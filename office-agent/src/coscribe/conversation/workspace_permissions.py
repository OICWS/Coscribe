"""The `permissions` of a workspace's accepted `.coscribe/settings.json` (decision 0048), shaped
like Claude Code's `.claude/settings.json`: `deny`, `ask` and `allow` lists of rules.

A rule is a coscribe tool name, a `*` pattern of names (`fetch_*`, a connector's `github_*`),
or either with a pattern of its main argument in brackets: `run_background_command(git status*)`,
`write_file(docs/*)`. Claude Code's own tool names (`Bash`, `Read`) and its `:*` prefix syntax
mean nothing here. They decide only the calls that would otherwise wait for an approval. Deny
wins over ask, ask over allow.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from fnmatch import fnmatchcase
from pathlib import Path
from typing import Any, Literal

FolderVerdict = Literal["deny", "ask", "allow"]
_ORDER: tuple[FolderVerdict, ...] = ("deny", "ask", "allow")
# The one argument a bracketed pattern is matched against. A call holding more than one of them
# could put the allowed text in a field the tool ignores, so such a call is never allowed by an
# argument pattern, and deny and ask look at every one.
_MAIN_ARGUMENTS = ("script", "command", "path", "file_path", "url", "query")
_PATH_ARGUMENTS = ("path", "file_path")
_COMMAND_ARGUMENTS = ("script", "command")
# `*` would match across these, so `git status*` would allow `git status && curl ... | sh`.
_CHAINING = re.compile(r"[;&|`\n\r]|\$\(")
_RULE = re.compile(r"^([A-Za-z0-9_*.\-]+)(?:\((.*)\))?$", re.DOTALL)
_MAX_RULES = 200


def _normalized_path(value: str, root: Path) -> str:
    """The path as the file tools will reach it: relative to the root when inside it, with `/`
    separators, `..` folded and, on Windows, lower case, so a rule can't be stepped around by
    spelling the same file another way."""
    base = os.path.normcase(os.path.normpath(root))
    joined = os.path.normcase(os.path.normpath(os.path.join(base, value)))
    try:
        inside = os.path.commonpath([joined, base]) == base
    except ValueError:
        inside = False
    shown = os.path.relpath(joined, base) if inside else joined
    return shown.replace("\\", "/")


@dataclass(frozen=True)
class _Rule:
    tool: str
    argument: str | None

    def matches(self, verdict: FolderVerdict, name: str, args: dict[str, Any], root: Path) -> bool:
        if not fnmatchcase(name, self.tool):
            return False
        if self.argument is None:
            return True
        present = [key for key in _MAIN_ARGUMENTS if key in args]
        if verdict == "allow" and len(present) != 1:
            return False
        for key in present:
            value = args[key]
            if not isinstance(value, str):
                continue
            if key in _PATH_ARGUMENTS:
                value = _normalized_path(value, root)
            if verdict == "allow" and key in _COMMAND_ARGUMENTS and _CHAINING.search(value):
                return False
            if fnmatchcase(value, self.argument):
                return True
        return False

    def shown(self) -> str:
        return self.tool if self.argument is None else f"{self.tool}({self.argument})"


def _rules(raw: Any, verdict: FolderVerdict) -> list[_Rule]:
    if not isinstance(raw, list):
        return []
    rules = []
    for item in raw[:_MAX_RULES]:
        match = _RULE.match(item.strip()) if isinstance(item, str) else None
        if not match:
            continue
        rule = _Rule(match.group(1), match.group(2))
        # Allowing every tool at once is the whole approval switched off by a file.
        if verdict == "allow" and rule.argument is None and not rule.tool.strip("*"):
            continue
        rules.append(rule)
    return rules


class WorkspacePermissions:
    def __init__(self, settings: dict[str, Any], root: Path) -> None:
        raw = settings.get("permissions")
        raw = raw if isinstance(raw, dict) else {}
        self._root = root
        self._lists = {verdict: _rules(raw.get(verdict), verdict) for verdict in _ORDER}

    def decide(
        self, name: str, args: dict[str, Any], risk: str | None = None
    ) -> tuple[FolderVerdict, str] | None:
        """The first list holding a rule for this call, and the rule, or None. A file the person
        accepted never allows a call that leaves the machine (`EXTERNAL`): those still ask."""
        for verdict in _ORDER:
            if verdict == "allow" and risk == "EXTERNAL":
                continue
            for rule in self._lists[verdict]:
                if rule.matches(verdict, name, args, self._root):
                    return verdict, rule.shown()
        return None
