from pathlib import Path

import pytest

from .helpers import (
    _tools_by_name,
)


def test_set_pptx_notes_round_trips_via_python_pptx(tmp_path: Path) -> None:
    from pptx import Presentation

    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- body")

    tools["set_pptx_notes"](path="deck.pptx", slide=1, notes="Remember to smile.")

    prs = Presentation(tmp_path / "deck.pptx")
    assert prs.slides[0].notes_slide.notes_text_frame.text == "Remember to smile."


def test_set_pptx_notes_replaces_rather_than_appends(tmp_path: Path) -> None:
    from pptx import Presentation

    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- body")

    tools["set_pptx_notes"](path="deck.pptx", slide=1, notes="First draft")
    tools["set_pptx_notes"](path="deck.pptx", slide=1, notes="Final version")

    prs = Presentation(tmp_path / "deck.pptx")
    assert prs.slides[0].notes_slide.notes_text_frame.text == "Final version"


def test_set_pptx_notes_out_of_range_slide_names_real_count(tmp_path: Path) -> None:
    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- body")

    with pytest.raises(ValueError, match="1 slides"):
        tools["set_pptx_notes"](path="deck.pptx", slide=5, notes="x")


def test_set_pptx_notes_is_medium_risk_and_requires_approval(tmp_path: Path) -> None:
    from coscribe.runtime import get_tool_metadata

    tools = _tools_by_name(tmp_path)
    metadata = get_tool_metadata(tools["set_pptx_notes"])
    assert metadata.risk_category == "WRITE_LOCAL"
    assert metadata.requires_approval is True
