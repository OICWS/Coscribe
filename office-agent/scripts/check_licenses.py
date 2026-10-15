"""Fails when a dependency of the installed environment carries a strong-copyleft licence.

    pip-licenses --format=json | python scripts/check_licenses.py

LGPL and MPL stay allowed: they bind the library's own files, not the application that
imports it. An unknown licence is listed but does not fail, because a package with no
metadata is a question for a person, not a build error.
"""

from __future__ import annotations

import json
import re
import sys
from typing import Any

# A GPL or AGPL or SSPL licence, but not the "L" in LGPL or "Lesser" GPL.
_STRONG_COPYLEFT = re.compile(
    r"(?<![A-Za-z])(AGPL|GPL|SSPL)|Affero General Public|(?<!Lesser )(?<!Library )General Public License",
    re.IGNORECASE,
)
_WEAK = re.compile(r"LGPL|Lesser General Public|Library General Public", re.IGNORECASE)


def strong_copyleft(packages: list[dict[str, Any]]) -> list[str]:
    """`name version: licence` for each package whose licence needs source disclosure."""
    found = []
    for package in packages:
        licence = str(package.get("License", ""))
        # "GPL-2.0 OR MIT" can be taken under MIT, so a dual licence that also offers a
        # permissive one passes.
        options = re.split(r"\s+OR\s+|;", licence)
        if any(not _STRONG_COPYLEFT.search(o) or _WEAK.search(o) for o in options):
            continue
        found.append(f"{package.get('Name')} {package.get('Version')}: {licence}")
    return found


def main() -> int:
    packages = json.load(sys.stdin)
    unknown = [p["Name"] for p in packages if str(p.get("License", "")).upper() == "UNKNOWN"]
    if unknown:
        print("No licence metadata (check by hand):", ", ".join(sorted(unknown)))
    found = strong_copyleft(packages)
    for line in found:
        print("Strong copyleft:", line)
    return 1 if found else 0


if __name__ == "__main__":
    raise SystemExit(main())
