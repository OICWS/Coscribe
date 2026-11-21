"""Refresh the bundled model catalog from models.dev and say what changed (decision 0055).

    python office-agent/scripts/update_model_catalog.py [--summary FILE]

Writes `src/coscribe/runtime/models/catalog.json` from https://models.dev/api.json and prints the
models added and removed and the capabilities that changed; `--summary` also writes that as
Markdown, which the scheduled job puts in its pull request. Exits 0 either way.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from coscribe.runtime.models.catalog import CATALOG_PATH, SOURCE_URL, dumps, trim  # noqa: E402

_LISTED = 40


def fetch() -> dict[str, Any]:
    request = urllib.request.Request(SOURCE_URL, headers={"User-Agent": "coscribe-catalog"})
    with urllib.request.urlopen(request, timeout=60) as response:
        data: dict[str, Any] = json.load(response)
    return data


def changes(old: dict[str, Any], new: dict[str, Any]) -> list[str]:
    """Markdown lines: the models added, removed and changed between two catalogs."""
    before, after = old.get("models", {}), new["models"]
    added = sorted(after.keys() - before.keys())
    removed = sorted(before.keys() - after.keys())
    changed = []
    for key in sorted(after.keys() & before.keys()):
        diff = [
            f"{field} {before[key].get(field)!r} -> {after[key].get(field)!r}"
            for field in sorted(before[key].keys() | after[key].keys())
            if field != "name" and before[key].get(field) != after[key].get(field)
        ]
        if diff:
            changed.append(f"`{key}`: " + "; ".join(diff))
    lines: list[str] = []
    for title, rows in (("Added", added), ("Removed", removed), ("Changed", changed)):
        if not rows:
            continue
        lines.append(f"### {title} ({len(rows)})")
        lines += [f"- {r}" if r.startswith("`") else f"- `{r}`" for r in rows[:_LISTED]]
        if len(rows) > _LISTED:
            lines.append(f"- and {len(rows) - _LISTED} more")
    return lines


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary", type=Path, help="also write the changes here, as Markdown")
    args = parser.parse_args()

    old = json.loads(CATALOG_PATH.read_text(encoding="utf-8")) if CATALOG_PATH.exists() else {}
    new = trim(fetch())
    CATALOG_PATH.write_text(dumps(new), encoding="utf-8")
    lines = changes(old, new) or ["No change."]
    print("\n".join(lines))
    if args.summary:
        args.summary.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
