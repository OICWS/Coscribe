"""The living documents say what is true now.

A document that still says what a later decision overturned misleads every session that reads it:
`SECURITY.md` said "There is no sandbox" a week after scripts began to run in an AppContainer
(decision 0021), and the README described tools that had been removed. Three checks keep that
from passing silently:

- a code name in backticks (`write_xlsx`, `look_at_page()`) must still be a word of the code;
- wording a decision retired (its `Retired wording:` line) must be gone from the living documents;
- a decision that supersedes, replaces, narrows or changes another is named in that one's status
  line and in its row of the decisions index, so a reader of the old record learns it is not the
  whole truth.

The documents that record history are not checked (`docs/history`, `docs/log`,
`docs/assessments`, the decision records themselves, the roadmap index, `PPTX_DESIGN.md`, the
runtime README), nor `docs/plan.md`, which names what does not exist yet.
"""

from __future__ import annotations

import re
import subprocess
from functools import cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DECISIONS = ROOT / "docs" / "decisions"

NOT_LIVING = (
    "docs/history/",
    "docs/log/",
    "docs/assessments/",
    "docs/decisions/",
    "docs/metrics/",
    "docs/plan.md",
    "office-agent/ROADMAP.md",
    "office-agent/PPTX_DESIGN.md",
    "office-agent/src/coscribe/runtime_lg/README.md",
    "office-agent/src/coscribe/builtin_skills/",
    "office-agent/frontend/node_modules/",
    "site/",
)
CODE = (
    "office-agent/src/",
    "office-agent/frontend/src/",
    "office-agent/frontend/tests/",
    "office-agent/scripts/",
    "office-agent/tests/",
    "office-agent/evals/",
    "office-agent-desktop/",
    ".github/",
    "office-agent/pyproject.toml",
    "office-agent/.env.example",
)
# Names that belong to someone else's code or to the person's machine, not to ours.
NOT_OURS = {
    "_format_image",  # langchain_anthropic
    "npm_config_noproxy",
    "send_later",  # a tool of the cloud session, not of coscribe
}

_NAME = re.compile(r"`([A-Za-z_][A-Za-z0-9]*(?:_[A-Za-z0-9]+)+)(?:\(\))?`")
_WORD = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_RETIRED = re.compile(r"^Retired wording:\s*(.+)$", re.M)
_QUOTED = re.compile(r'"([^"]+)"')
_LATER = re.compile(r"\b(?:Supersedes|Replaces|Narrows|Changes)\b[^.]*?\b(0\d{3})\b")


def _tracked() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    return result.stdout.splitlines()


def living_documents() -> list[str]:
    return [
        name
        for name in _tracked()
        if name.endswith(".md") and not name.startswith(NOT_LIVING) and (ROOT / name).is_file()
    ]


@cache
def _code_words() -> frozenset[str]:
    words: set[str] = set()
    for name in _tracked():
        path = ROOT / name
        if not name.startswith(CODE) or not path.is_file() or path.stat().st_size > 2_000_000:
            continue
        words.update(_WORD.findall(path.read_text(encoding="utf-8", errors="ignore")))
    return frozenset(words)


def gone_names(text: str, code_words: frozenset[str]) -> list[str]:
    """The code names in backticks that are no longer a word of the code."""
    return sorted(
        {
            name
            for name in _NAME.findall(text)
            if name not in code_words and name not in NOT_OURS and not name.isupper()
        }
    )


def test_a_code_name_a_living_document_gives_still_exists() -> None:
    words = _code_words()
    stale = [
        f"{name}: `{gone}`"
        for name in living_documents()
        for gone in gone_names((ROOT / name).read_text(encoding="utf-8"), words)
    ]
    assert not stale, "Named in a document but no longer in the code:\n" + "\n".join(stale)


def _records() -> dict[str, str]:
    return {path.name[:4]: path.read_text(encoding="utf-8") for path in DECISIONS.glob("0*.md")}


def test_wording_a_decision_retired_is_gone_from_the_living_documents() -> None:
    retired = {
        phrase: number
        for number, text in _records().items()
        for line in _RETIRED.findall(text)
        for phrase in _QUOTED.findall(line)
    }
    assert retired, "no decision lists retired wording; the check would check nothing"
    found = [
        f"{name}: {phrase!r} (retired by {number})"
        for name in living_documents()
        for phrase, number in retired.items()
        if phrase.lower() in (ROOT / name).read_text(encoding="utf-8").lower()
    ]
    assert not found, "Still says what a decision retired:\n" + "\n".join(found)


def _status(text: str) -> str:
    """A record's status: from its `Status:` line to the first blank line."""
    match = re.search(r"^Status:(.*?)(?:\n\s*\n|\Z)", text, re.M | re.S)
    return match.group(1) if match else ""


def test_a_superseded_decision_says_so_in_its_status_and_in_the_index() -> None:
    records = _records()
    index = (DECISIONS / "README.md").read_text(encoding="utf-8")
    rows = {m.group(1): m.group(0) for m in re.finditer(r"^\| \[(0\d{3})\].*$", index, re.M)}
    missing = []
    for later, text in records.items():
        for earlier in set(_LATER.findall(_status(text))):
            if earlier == later or earlier not in records:
                continue
            if later not in _status(records[earlier]):
                missing.append(f"{earlier}'s status does not name {later}")
            if later not in rows.get(earlier, ""):
                missing.append(f"the index row of {earlier} does not name {later}")
    assert not missing, "\n".join(missing)


def test_the_checks_catch_what_they_are_for() -> None:
    words = frozenset({"look_at_page", "write_xlsx_cells"})
    text = "Use `look_at_page()`, `write_xlsx_cells`, `write_xlsx` and `COSCRIBE_NOT_A_NAME`."
    assert gone_names(text, words) == ["write_xlsx"]
    assert _LATER.findall("accepted. Supersedes the part of 0015 and narrows 0019.") == ["0015"]
    assert _status("# 0001\n\nStatus: accepted; superseded by 0021.\n\n## Context") == (
        " accepted; superseded by 0021."
    )
