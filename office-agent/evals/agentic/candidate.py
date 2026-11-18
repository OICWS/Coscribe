"""Start an evaluation task from a failed turn a person exported from the app (decision 0051).

    python -m evals.agentic.candidate failed-turn-20261118103000.json

Prints an `AgenticTask` to paste into `agentic/tasks.py`, with what the turn left behind as
comments. The file holds no conversation words and no files, so the turns are the person's own
summary at best, and the setup and checks are written by hand before the task runs.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

FORMAT = "coscribe-failed-turn/1"


def _comment(text: str) -> str:
    return " ".join(str(text).split())


def task_source(exported: dict[str, Any], name: str) -> str:
    """The Python of a task that starts from the exported turn."""
    if exported.get("format") != FORMAT:
        raise ValueError(f"not a {FORMAT} file")
    turn = exported.get("turn") or {}
    lines = [
        f"# From a turn exported by coscribe {exported.get('coscribe', '?')}, started"
        f" {turn.get('started', '?')}.",
        f"# {turn.get('model', '?')} at {turn.get('effort', '?')} effort, {turn.get('mode', '?')}"
        f" mode: {turn.get('model_calls', 0)} model calls in {turn.get('seconds', '?')} s,"
        f" ended {turn.get('outcome', '?')}"
        + (f" ({turn['error']})" if turn.get("error") else "")
        + ".",
    ]
    for tool, count in sorted((turn.get("tools") or {}).items()):
        lines.append(f"#   {tool}: {count.get('calls', 0)} calls, {count.get('errors', 0)} failed")
    for error in exported.get("tool_errors") or []:
        lines.append(f"#   {error.get('tool', '?')} said: {_comment(error.get('text', ''))}")
    if exported.get("went_wrong"):
        lines.append(
            f"# What went wrong, in the person's words: {_comment(exported['went_wrong'])}"
        )
    asked = str(exported.get("asked") or "").strip() or "TODO: what the person asked for"
    lines += [
        "AgenticTask(",
        f"    name={name!r},",
        f"    turns=({asked!r},),",
        "    setup=lambda root: None,  # TODO: the files the turn worked on",
        "    checks={},  # TODO: what the finished conversation must show",
        ")",
    ]
    return "\n".join(lines) + "\n"


def _name(exported: dict[str, Any]) -> str:
    """A name from the tool that failed most, the way the tasks are named by what they test."""
    tools = (exported.get("turn") or {}).get("tools") or {}
    worst = max(tools.items(), key=lambda item: item[1].get("errors", 0), default=(None, {}))
    if worst[0] and worst[1].get("errors"):
        return "failed-" + re.sub(r"[^a-z0-9]+", "-", worst[0].lower()).strip("-")
    return f"failed-{(exported.get('turn') or {}).get('outcome', 'turn')}"


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("file", type=Path, help="a failed-turn-*.json file from the app")
    parser.add_argument("--name", help="the task's name (default: from the tool that failed)")
    args = parser.parse_args(argv)
    try:
        exported = json.loads(args.file.read_text(encoding="utf-8"))
        sys.stdout.write(task_source(exported, args.name or _name(exported)))
    except (OSError, ValueError) as error:
        print(f"{args.file}: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
