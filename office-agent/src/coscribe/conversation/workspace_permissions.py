"""The `permissions` of a workspace's accepted `.coscribe/settings.json` (decision 0048), as
Claude Code's `.claude/settings.json` holds them: `deny`, `ask` and `allow` lists of rules.

A rule is a coscribe tool name, a `*` pattern of names (`fetch_*`, a connector's `github_*`),
or either with a pattern of its main argument in brackets: `run_command(git status*)`. They
decide only the calls that would otherwise wait for an approval. Deny wins over ask, ask over
allow, as in Claude Code.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from fnmatch import fnmatchcase
from typing import Any, Literal

FolderVerdict = Literal["deny", "ask", "allow"]
_ORDER: tuple[FolderVerdict, ...] = ("deny", "ask", "allow")
# The one argument a bracketed pattern is matched against: matching any argument would let a
# call put the allowed text in a field nobody reads and the real command in another.
_MAIN_ARGUMENTS = ("script", "command", "path", "file_path", "url", "query")
_RULE = re.compile(r"^([A-Za-z0-9_*.\-]+)(?:\((.*)\))?$", re.DOTALL)
_MAX_RULES = 200


@dataclass(frozen=True)
class _Rule:
    tool: str
    argument: str | None

    def matches(self, name: str, args: dict[str, Any]) -> bool:
        if not fnmatchcase(name, self.tool):
            return False
        if self.argument is None:
            return True
        main = next((args[key] for key in _MAIN_ARGUMENTS if key in args), None)
        return isinstance(main, str) and fnmatchcase(main, self.argument)


def _rules(raw: Any) -> list[_Rule]:
    if not isinstance(raw, list):
        return []
    rules = []
    for item in raw[:_MAX_RULES]:
        match = _RULE.match(item.strip()) if isinstance(item, str) else None
        if match:
            rules.append(_Rule(match.group(1), match.group(2)))
    return rules


class WorkspacePermissions:
    def __init__(self, settings: dict[str, Any]) -> None:
        raw = settings.get("permissions")
        raw = raw if isinstance(raw, dict) else {}
        self._lists = {verdict: _rules(raw.get(verdict)) for verdict in _ORDER}

    def decide(self, name: str, args: dict[str, Any]) -> tuple[FolderVerdict, str] | None:
        """The first list holding a rule for this call, and the rule, or None."""
        for verdict in _ORDER:
            for rule in self._lists[verdict]:
                if rule.matches(name, args):
                    shown = rule.tool if rule.argument is None else f"{rule.tool}({rule.argument})"
                    return verdict, shown
        return None
