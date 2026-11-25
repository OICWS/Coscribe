#!/usr/bin/env python3
"""Whether each component's card (its AGENTS.md) has kept up with the component's code.

    python scripts/card_freshness.py                  how many commits each card is behind
    git diff --name-only origin/main... | python scripts/card_freshness.py --changed

A card is behind by the commits to the component's own files (not those of components nested
in it, not the card) since the card last changed. Its interface and dependencies are checked
by tests, but its Purpose and Invariants are prose that drifts silently. With `--changed`, a
pull request fails when it changes the code of a component whose card is `LIMIT` or more
commits behind and does not change that card: whoever touches the component next reads the
card against the code and updates its `## Reviewed` section (decision 0009's "cards stay true").
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import tomllib
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
COMPONENTS = REPO / "components.toml"
LIMIT = 20


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(REPO), *args], capture_output=True, text=True, check=True
    ).stdout


def components(toml: Path = COMPONENTS) -> list[dict[str, str]]:
    found: list[dict[str, str]] = tomllib.loads(toml.read_text("utf-8")).get("component", [])
    return found


def nested(component: dict[str, str], every: list[dict[str, str]]) -> list[str]:
    """The paths of the components inside this one, which own their files."""
    root = component["path"].rstrip("/") + "/"
    return [c["path"] for c in every if c is not component and c["path"].startswith(root)]


def owns(component: dict[str, str], every: list[dict[str, str]], path: str) -> bool:
    root = component["path"]
    inside = path == root or path.startswith(root.rstrip("/") + "/")
    return (
        inside
        and path != component.get("card")
        and not any(path == n or path.startswith(n + "/") for n in nested(component, every))
    )


def behind(component: dict[str, str], every: list[dict[str, str]], head: str = "HEAD") -> int:
    card = component["card"]
    since = _git("log", "-1", "--format=%H", head, "--", card).strip()
    if not since:
        return 0
    excluded = [f":!{card}", *(f":!{n}" for n in nested(component, every))]
    count = _git("rev-list", "--count", f"{since}..{head}", "--", component["path"], *excluded)
    return int(count.strip() or 0)


def problems(changed: list[str], lag: dict[str, int], every: list[dict[str, str]]) -> list[str]:
    """`lag`: component name -> commits its card is behind, for the components with a card."""
    found = []
    for component in every:
        name, card = component["name"], component.get("card")
        if not card or lag.get(name, 0) < LIMIT or card in changed:
            continue
        if any(owns(component, every, path) for path in changed):
            found.append(
                f"{name}: its card ({card}) is {lag[name]} commits behind the code this pull "
                f"request changes. Read it against the code, correct what no longer holds and "
                f"update its `## Reviewed` section in this pull request."
            )
    return found


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--changed", action="store_true", help="read changed paths from stdin")
    args = parser.parse_args(argv)
    every = components()
    with_card = [c for c in every if c.get("card")]
    if not args.changed:
        for component in with_card:
            print(f"{behind(component, every):4d}  {component['name']}")
        return 0
    changed = [line.strip() for line in sys.stdin if line.strip()]
    touched = [c for c in with_card if any(owns(c, every, p) for p in changed)]
    lag = {c["name"]: behind(c, every) for c in touched}
    found = problems(changed, lag, every)
    for line in found:
        print(f"::error::{line}")
    return 1 if found else 0


if __name__ == "__main__":
    raise SystemExit(main())
