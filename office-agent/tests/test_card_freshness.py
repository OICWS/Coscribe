"""scripts/card_freshness.py: a card far behind its code is updated by the next change to it."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "card_freshness.py"

TOOLS = {"name": "tools", "path": "src/tools", "card": "src/tools/AGENTS.md"}
PPTX = {"name": "tools.pptx", "path": "src/tools/pptx", "card": "src/tools/pptx/AGENTS.md"}
CLI = {"name": "cli", "path": "src/cli.py"}
EVERY = [TOOLS, PPTX, CLI]


@pytest.fixture(scope="module")
def cards() -> ModuleType:
    spec = importlib.util.spec_from_file_location("card_freshness", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["card_freshness"] = module
    spec.loader.exec_module(module)
    return module


def test_a_component_owns_its_files_but_not_its_card_or_a_nested_component(
    cards: ModuleType,
) -> None:
    assert cards.owns(TOOLS, EVERY, "src/tools/files.py")
    assert not cards.owns(TOOLS, EVERY, "src/tools/AGENTS.md")
    assert not cards.owns(TOOLS, EVERY, "src/tools/pptx/deck.py")
    assert not cards.owns(TOOLS, EVERY, "src/toolsmith.py")
    assert cards.owns(PPTX, EVERY, "src/tools/pptx/deck.py")


def test_a_change_to_a_component_far_behind_fails_unless_it_updates_the_card(
    cards: ModuleType,
) -> None:
    lag = {"tools": cards.LIMIT, "tools.pptx": cards.LIMIT - 1}
    found = cards.problems(["src/tools/files.py"], lag, EVERY)
    assert len(found) == 1 and found[0].startswith("tools: its card")
    assert cards.problems(["src/tools/files.py", "src/tools/AGENTS.md"], lag, EVERY) == []
    assert cards.problems(["src/tools/pptx/deck.py"], lag, EVERY) == []  # not far enough behind
    assert cards.problems(["docs/plan.md"], lag, EVERY) == []


def test_behind_counts_the_commits_to_the_code_since_the_card_last_changed(
    cards: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def git(*args: str) -> None:
        subprocess.run(["git", "-C", str(tmp_path), *args], check=True, capture_output=True)

    git("init", "-q")
    git("config", "user.email", "t@example.com")
    git("config", "user.name", "t")
    (tmp_path / "src" / "tools" / "pptx").mkdir(parents=True)

    def commit(path: str, text: str) -> None:
        (tmp_path / path).write_text(text, encoding="utf-8")
        git("add", "-A")
        git("commit", "-q", "-m", path)

    commit("src/tools/AGENTS.md", "card")
    commit("src/tools/a.py", "1")
    commit("src/tools/pptx/deck.py", "1")  # a nested component's file
    commit("src/tools/a.py", "2")
    monkeypatch.setattr(cards, "REPO", tmp_path)
    assert cards.behind(TOOLS, EVERY) == 2
    commit("src/tools/AGENTS.md", "card, reviewed")
    assert cards.behind(TOOLS, EVERY) == 0
