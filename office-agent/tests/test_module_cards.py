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
CARDS = sorted([*SRC.glob("*/AGENTS.md"), *SRC.glob("tools/office/*/AGENTS.md")])
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


def _dotted(card: Path) -> str:
    return ".".join(["coscribe", *card.parent.relative_to(SRC).parts])


@pytest.mark.parametrize("card", CARDS, ids=lambda p: _dotted(p))
def test_a_card_has_the_fixed_headings_and_stays_short(card: Path) -> None:
    text = card.read_text(encoding="utf-8")
    assert re.findall(r"^## (.+)$", text, re.M) == HEADINGS
    assert text.startswith("# ")
    assert len(text.splitlines()) <= MAX_LINES
    assert card.with_name("CLAUDE.md").read_text(encoding="utf-8").strip() == "@AGENTS.md"


def _reexported_from_sub_components(card: Path) -> set[str]:
    """Names a package re-exports from a sub-package of its own: the sub-component's card lists
    them (its own test), so the parent's card need not list them again (issue #677)."""
    found: set[str] = set()
    for init in card.parent.glob("**/__init__.py"):
        if init.parent == card.parent:
            continue
        found |= set(getattr(importlib.import_module(_dotted_of(init.parent)), "__all__", []))
    return found


def _dotted_of(directory: Path) -> str:
    return ".".join(["coscribe", *directory.relative_to(SRC).parts])


@pytest.mark.parametrize("card", CARDS, ids=lambda p: _dotted(p))
def test_a_cards_public_interface_is_the_packages_all(card: Path) -> None:
    package = importlib.import_module(_dotted(card))
    section = _section(card.read_text(encoding="utf-8"), "Public interface")
    missing = set(package.__all__) - _names(section) - _reexported_from_sub_components(card)
    assert not missing, f"exported but not on the card: {sorted(missing)}"


def _depends_on_name(imported: str, component: str) -> str:
    """The unit a card names for an import: a sibling inside the component's parent package,
    otherwise a module of the same top-level package, otherwise another top-level package."""
    parts = imported.split(".")
    parent = component.split(".")[:-1]
    if len(parent) > 1 and parts[: len(parent)] == parent:
        return ".".join(parts[: len(parent) + 1])
    if len(parent) > 1 and parts[:2] == component.split(".")[:2]:
        return ".".join(parts[:3])
    return ".".join(parts[:2])


@pytest.mark.parametrize("card", CARDS, ids=lambda p: _dotted(p))
def test_a_cards_dependencies_are_what_the_package_imports(card: Path) -> None:
    name = _dotted(card)
    graph = grimp.build_graph("coscribe")
    actual = {
        _depends_on_name(imported, name)
        for module in graph.find_descendants(name)
        for imported in graph.find_modules_directly_imported_by(module)
        if imported != name and not imported.startswith(f"{name}.")
    }
    section = _section(card.read_text(encoding="utf-8"), "Depends on")
    stated = set(re.findall(r"`(coscribe(?:\.[A-Za-z_0-9]+)*)`", section))
    assert stated == actual
