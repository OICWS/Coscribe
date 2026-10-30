"""Which living documents a pull request's change can make untrue, and whether each was looked at.

`docs/doc-map.toml` names, for each document, the paths whose change can make it untrue. For a
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


def load_map(path: Path = DOC_MAP) -> dict[str, list[str]]:
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    return {entry["path"]: list(entry["covers"]) for entry in data["doc"]}


def affected(changed: list[str], doc_map: dict[str, list[str]]) -> dict[str, list[str]]:
    """Each document whose covered paths changed, with the changed files that touch it."""
    found: dict[str, list[str]] = {}
    for doc, covers in doc_map.items():
        touching = [f for f in changed if f != doc and any(f.startswith(c) for c in covers)]
        if touching:
            found[doc] = touching
    return found


def not_looked_at(
    changed: list[str], body: str, doc_map: dict[str, list[str]]
) -> dict[str, list[str]]:
    """The affected documents the change neither edits nor names on a `Docs checked:` line."""
    # Whole paths, so that naming office-agent/README.md does not also check README.md.
    named = set(_PATH.findall(" ".join(_CHECKED.findall(body or ""))))
    return {
        doc: files
        for doc, files in affected(changed, doc_map).items()
        if doc not in changed and doc not in named
    }


def _changed_files(base: str, head: str) -> list[str]:
    result = subprocess.run(
        ["git", "diff", "--name-only", f"{base}...{head}"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    return [line for line in result.stdout.splitlines() if line]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default="origin/main")
    parser.add_argument("--head", default="HEAD")
    args = parser.parse_args(argv)
    missing = not_looked_at(
        _changed_files(args.base, args.head), os.environ.get("PR_BODY", ""), load_map()
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
