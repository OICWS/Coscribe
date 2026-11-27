"""Check that each row of the web search table still matches its source (`web_search.json`).

    python office-agent/scripts/check_web_search_sources.py [--summary FILE]

For each provider row, reads its `source` page and looks for every phrase in its `expect` list
(the endpoint paths, the price line). Prints what is missing or unreadable; `--summary` writes
that as Markdown for the scheduled job's issue. The table is kept by hand, so nothing is changed
here. Exits 0 either way; the summary file exists only when something needs a look.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from collections.abc import Callable
from pathlib import Path
from typing import Any

TABLE_PATH = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "coscribe"
    / "runtime"
    / "models"
    / "web_search.json"
)


def read(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": "coscribe-catalog"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return str(response.read().decode("utf-8", "replace"))


def findings(table: dict[str, dict[str, Any]], fetch: Callable[[str], str] = read) -> list[str]:
    """One line per row whose source can't be read or no longer says what the row relies on."""
    lines: list[str] = []
    for pid, row in table.items():
        source = str(row["source"])
        try:
            text = fetch(source)
        except OSError as exc:
            lines.append(f"- `{pid}`: couldn't read {source} ({exc})")
            continue
        for phrase in row.get("expect") or []:
            if str(phrase) not in text:
                lines.append(f"- `{pid}`: {source} no longer says `{phrase}`")
    return lines


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--summary", type=Path)
    args = parser.parse_args()
    table = json.loads(TABLE_PATH.read_text(encoding="utf-8"))["providers"]
    lines = findings(table)
    print("\n".join(lines) if lines else f"All {len(table)} web search rows match their sources.")
    if lines and args.summary:
        args.summary.write_text(
            "The web search table (`office-agent/src/coscribe/runtime/models/web_search.json`) no "
            "longer matches these sources. Check each provider's page, then fix the row (its "
            "paths, `expect` and `checked` date) or remove it.\n\n" + "\n".join(lines) + "\n",
            encoding="utf-8",
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
