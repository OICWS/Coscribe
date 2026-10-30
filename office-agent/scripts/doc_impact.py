"""Which living documents a pull request's change can make untrue, and whether each was looked at.

`docs/doc-map.toml` names, for each document, the paths whose change can make it untrue. A module's
card (the `AGENTS.md` beside its code) lists what each of its files does, so it is affected when the
module gains, loses or renames a file or changes its `__init__.py`; edits inside existing files do
not ask for it, since the card's interface is checked by `tests/test_module_cards.py`. For a
document whose paths changed, the pull request either changes the document too or says in its
description that it still holds, on a line that starts with `Docs checked:` and names it:

    Docs checked: SECURITY.md (the sandbox wording still holds), ARCHITECTURE.md

Run by the PR text workflow with the description in `PR_BODY`; locally, to see what to read
before opening a pull request:

    python office-agent/scripts/doc_impact.py --base origin/main
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOC_MAP = ROOT / "docs" / "doc-map.toml"
_CHECKED = re.compile(r"^\s*[-*]?\s*Docs checked:(.*)$", re.I | re.M)
_PATH = re.compile(r"(?<![\w/.-])[\w./-]+\.md\b")


Changes = list[tuple[str, str]]
DocMap = dict[str, dict[str, list[str]]]


def load_map(path: Path = DOC_MAP) -> DocMap:
    """Each document's `covers` (any change counts) and `added_or_removed` (only a file added,
    removed or renamed counts)."""
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    return {
        entry["path"]: {
            "covers": list(entry.get("covers", [])),
            "added_or_removed": list(entry.get("added_or_removed", [])),
        }
        for entry in data["doc"]
    }


def affected(changes: Changes, doc_map: DocMap) -> dict[str, list[str]]:
    """Each document whose covered paths changed, with the changed files that touch it."""
    found: dict[str, list[str]] = {}
    for doc, paths in doc_map.items():
        touching = [
            f
            for status, f in changes
            if f != doc
            and (
                any(f.startswith(c) for c in paths["covers"])
                or (status[0] in "ADR" and any(f.startswith(c) for c in paths["added_or_removed"]))
            )
        ]
        if touching:
            found[doc] = touching
    return found


def cards_affected(changes: Changes, cards: list[str]) -> dict[str, list[str]]:
    """Each module card whose module gained, lost or renamed a file, or changed `__init__.py`;
    a change counts for the nearest card above it."""
    dirs = sorted((card.rsplit("/", 1)[0] + "/" for card in cards), key=len, reverse=True)
    found: dict[str, list[str]] = {}
    for status, path in changes:
        home = next((d for d in dirs if path.startswith(d)), None)
        if home is None or path == home + "AGENTS.md":
            continue
        if status[0] in "ADR" or path == home + "__init__.py":
            found.setdefault(home + "AGENTS.md", []).append(path)
    return found


def not_looked_at(
    changes: Changes,
    body: str,
    doc_map: DocMap,
    cards: dict[str, list[str]] | None = None,
) -> dict[str, list[str]]:
    """The affected documents the change neither edits nor names on a `Docs checked:` line."""
    # Whole paths, so that naming office-agent/README.md does not also check README.md.
    named = set(_PATH.findall(" ".join(_CHECKED.findall(body or ""))))
    changed = {path for _, path in changes}
    found = {**affected(changes, doc_map), **(cards or {})}
    return {doc: files for doc, files in found.items() if doc not in changed and doc not in named}


def _git(*args: str) -> list[str]:
    result = subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", check=True
    )
    return [line for line in result.stdout.splitlines() if line]


def _changes(base: str, head: str) -> Changes:
    """(status, path) for each changed file; a rename gives its old and its new path."""
    found: list[tuple[str, str]] = []
    for line in _git("diff", "--name-status", "-M", f"{base}...{head}"):
        status, *paths = line.split("\t")
        found.extend((status, path) for path in paths)
    return found


def module_cards() -> list[str]:
    """The cards of Python modules; the frontend's card is in the map, since a component added
    there does not change what its card says."""
    tracked = set(_git("ls-files", "office-agent/src"))
    return [
        name
        for name in tracked
        if name.endswith("/AGENTS.md") and name[: -len("AGENTS.md")] + "__init__.py" in tracked
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default="origin/main")
    parser.add_argument("--head", default="HEAD")
    args = parser.parse_args(argv)
    changes = _changes(args.base, args.head)
    missing = not_looked_at(
        changes,
        os.environ.get("PR_BODY", ""),
        load_map(),
        cards_affected(changes, module_cards()),
    )
    if not missing:
        print("Every document this change can make untrue was changed or checked.")
        return 0
    print("This change touches what these documents describe. Read each one; change it in this")
    print("pull request where it no longer holds, or add a line to the description:")
    print("  Docs checked: <path> (<why it still holds>)\n")
    for doc, files in missing.items():
        shown = ", ".join(files[:5]) + (f" and {len(files) - 5} more" if len(files) > 5 else "")
        print(f"::error::{doc} -- covers {shown}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
