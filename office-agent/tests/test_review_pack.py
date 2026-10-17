"""`scripts/review_pack.py`: what it picks out of a pull request for the reviewer."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "review_pack.py"


@pytest.fixture(scope="module")
def pack() -> ModuleType:
    spec = importlib.util.spec_from_file_location("review_pack", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["review_pack"] = module
    spec.loader.exec_module(module)
    return module


CODEOWNERS = """\
/office-agent/frontend/ @OICWS
# Invariant paths (office-agent/CLAUDE.md, decision 0007).
/office-agent/src/coscribe/runtime/secrets*.py @OICWS @kurtosisOC
/office-agent/quality/ @OICWS @kurtosisOC
"""


def test_invariant_paths_are_the_ones_listed_after_the_comment(pack: ModuleType) -> None:
    patterns = pack.invariant_patterns(CODEOWNERS)

    assert patterns == ["office-agent/src/coscribe/runtime/secrets*.py", "office-agent/quality/"]
    touched = pack.touched_invariants(
        [
            "office-agent/src/coscribe/runtime/secrets.py",
            "office-agent/quality/baseline.json",
            "office-agent/frontend/src/App.tsx",
        ],
        patterns,
    )
    assert touched == [
        "office-agent/src/coscribe/runtime/secrets.py",
        "office-agent/quality/baseline.json",
    ]


def test_a_new_name_or_a_bigger_number_is_marked_worse(pack: ModuleType) -> None:
    before = {"fan_out": {"a": 26, "b": 30}, "long_functions": {"f": 120}}
    after = {"fan_out": {"b": 31, "c": 26}, "long_functions": {"f": 110}}

    assert pack.ratchet_moves(before, after) == [
        "- better fan_out: a is gone (was 26)",
        "- WORSE fan_out: b 30 -> 31",
        "- WORSE fan_out: new c = 26",
        "- better long_functions: f 120 -> 110",
    ]


def test_the_not_verified_text_is_read_from_a_heading_or_a_label(pack: ModuleType) -> None:
    log = "# Title\n\n## Shipped\n- x\n\n## Not verified\n- a Windows run\n\n## Follow-ups\n- y\n"
    body = "Before: x.\n\nNot verified: no Windows run.\n"

    assert pack.not_verified(log) == "- a Windows run"
    assert pack.not_verified(body) == "no Windows run."
    assert pack.not_verified("nothing here") == ""


def test_the_pack_names_every_section_and_the_decisions_a_pr_links(pack: ModuleType) -> None:
    meta = {
        "number": 7,
        "title": "[x] y",
        "body": "See docs/decisions/0002-approvals-not-a-sandbox.md.\n\nNot verified: a real run.",
        "baseRefName": "main",
        "headRefName": "x/y",
        "additions": 3,
        "deletions": 1,
    }
    components = {"web": {"card": "AGENTS.md", "interface": ["router"], "files": ["a.py"]}}

    text = pack.render(meta, ["a.py"], components, ["a.py"], ["snap.txt"], [], {})

    for heading in (
        "## Components touched",
        "## Invariant paths touched",
        "## Snapshots changed",
        "## Ratchet numbers moved",
        "## Decisions linked",
        "## Not verified",
    ):
        assert heading in text
    assert "`docs/decisions/0002-approvals-not-a-sandbox.md`" in text
    assert "interface: router" in text
    assert "a real run." in text
