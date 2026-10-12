"""A component's card (`AGENTS.md` next to its `__init__.py`) must match the code.

A card is read instead of the source, so a card that drifts is worse than none: its headings
are fixed, it stays short, its public interface is `__all__`, and "Depends on" is what the
package really imports.
"""

from __future__ import annotations

import importlib
import re
from pathlib import Path

import grimp
import pytest

SRC = Path(__file__).resolve().parents[1] / "src" / "coscribe"
CARDS = sorted(SRC.glob("*/AGENTS.md"))
HEADINGS = [
    "Purpose",
    "Public interface",
    "Depends on",
    "Invariants",
    "Tests",
    "Verify by hand",
    "Reviewed",
]
MAX_LINES = 60


def _section(text: str, heading: str) -> str:
    match = re.search(rf"^## {re.escape(heading)}\n(.*?)(?=^## |\Z)", text, re.S | re.M)
    assert match, f"no '## {heading}' section"
    return match.group(1)


def _names(text: str) -> set[str]:
    return set(re.findall(r"`([A-Za-z_][A-Za-z_0-9]*)`", text))


@pytest.mark.parametrize("card", CARDS, ids=lambda p: p.parent.name)
def test_a_card_has_the_fixed_headings_and_stays_short(card: Path) -> None:
    text = card.read_text(encoding="utf-8")
    assert re.findall(r"^## (.+)$", text, re.M) == HEADINGS
    assert text.startswith("# ")
    assert len(text.splitlines()) <= MAX_LINES
    assert card.with_name("CLAUDE.md").read_text(encoding="utf-8").strip() == "@AGENTS.md"


@pytest.mark.parametrize("card", CARDS, ids=lambda p: p.parent.name)
def test_a_cards_public_interface_is_the_packages_all(card: Path) -> None:
    package = importlib.import_module(f"coscribe.{card.parent.name}")
    section = _section(card.read_text(encoding="utf-8"), "Public interface")
    missing = set(package.__all__) - _names(section)
    assert not missing, f"exported but not on the card: {sorted(missing)}"


@pytest.mark.parametrize("card", CARDS, ids=lambda p: p.parent.name)
def test_a_cards_dependencies_are_what_the_package_imports(card: Path) -> None:
    name = f"coscribe.{card.parent.name}"
    graph = grimp.build_graph("coscribe")
    actual = {
        ".".join(imported.split(".")[:2])
        for module in graph.find_descendants(name)
        for imported in graph.find_modules_directly_imported_by(module)
        if not imported.startswith(name)
    }
    section = _section(card.read_text(encoding="utf-8"), "Depends on")
    stated = set(re.findall(r"`(coscribe\.[a-z_]+)`", section))
    assert stated == actual
