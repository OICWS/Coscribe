"""Decide how much CI a pull request needs, from the files it changes (one path per stdin line).

Prints `scope=docs` when every changed file is documentation that only the documentation tests
read, else `scope=full`. The `test` job is a required check, so it always runs and reports; a
`paths:` filter would leave it unreported and block the merge. Markdown that the product reads
(a skill's SKILL.md, a template) is not documentation here.
"""

from __future__ import annotations

import re
import sys

DOCS = (
    re.compile(r"docs/.+"),
    re.compile(r"[^/]+\.md"),  # README, AGENTS, CLAUDE, ARCHITECTURE at the root
    re.compile(r"office-agent/[^/]+\.md"),  # CLAUDE, README, ROADMAP, PPTX_DESIGN
    re.compile(r"office-agent/src/coscribe/(?:[\w-]+/)*(?:AGENTS|CLAUDE)\.md"),  # package cards
)

DOCS_TESTS = (
    "tests/test_doc_references.py",
    "tests/test_docs_layout.py",
    "tests/test_file_sizes.py",
    "tests/test_module_cards.py",
)


def scope(paths: list[str]) -> str:
    changed = [p.strip() for p in paths if p.strip()]
    if changed and all(any(rule.fullmatch(p) for rule in DOCS) for p in changed):
        return "docs"
    return "full"


if __name__ == "__main__":
    if sys.argv[1:] == ["--tests"]:
        print(" ".join(DOCS_TESTS))
    else:
        print(f"scope={scope(sys.stdin.read().splitlines())}")
