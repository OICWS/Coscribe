"""The "Slides" guide the evaluation installs for decks written as HTML sections (decision 0015):
it loads as a skill, the runner swaps the coordinator's new-deck paragraph for it and back, and
every example it shows the model builds without an error, so the guide never teaches a slide the
compiler refuses."""

from __future__ import annotations

import re
import shutil
from pathlib import Path

from coscribe.tools import load_skills
from coscribe.tools.office.pptx.engine import check_sections, compile_sections
from evals.run import SECTIONS_GUIDE, deck_language

_TITLE = '<h2 id="title" style="left:96px;top:60px;width:1700px;height:80px">Example</h2>'


def _examples() -> list[str]:
    guide = (SECTIONS_GUIDE / "SKILL.md").read_text(encoding="utf-8")
    blocks = re.findall(r"```html\n(.*?)```", guide, re.S)
    return [
        b if b.lstrip().startswith("<section") else f"<section>{_TITLE}{b}</section>"
        for b in blocks
    ]


def test_the_guide_loads_as_the_slides_skill(tmp_path: Path) -> None:
    (tmp_path / "slides").mkdir()
    shutil.copyfile(SECTIONS_GUIDE / "SKILL.md", tmp_path / "slides" / "SKILL.md")
    assert [skill.name for skill in load_skills(tmp_path)] == ["Slides"]


def test_every_example_in_the_guide_builds_cleanly(tmp_path: Path) -> None:
    examples = _examples()
    assert len(examples) == 4
    pages = [(f"{i:02d}.html", text) for i, text in enumerate(examples, start=1)]
    report = compile_sections(pages, tmp_path / "deck.pptx", resource_root=tmp_path)
    check_sections(report)
    assert report.ok, report.errors()


def test_the_runner_swaps_the_new_deck_paragraph_and_puts_it_back() -> None:
    from coscribe import coordinator

    original = coordinator.NEW_DECK_INSTRUCTIONS
    with deck_language("sections"):
        assert 'load_skill("Slides")' in coordinator.NEW_DECK_INSTRUCTIONS
    assert coordinator.NEW_DECK_INSTRUCTIONS == original
    with deck_language("pages"):
        assert coordinator.NEW_DECK_INSTRUCTIONS == original
