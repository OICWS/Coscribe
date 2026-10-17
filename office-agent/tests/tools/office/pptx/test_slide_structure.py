from pathlib import Path

import pytest

from .helpers import (
    _make_test_png,
    _tools_by_name,
)

# --- delete/duplicate/reorder_pptx_slide (Tier 2 #4: deck structure editing) ---


def _titles(pptx_path: Path) -> list[str | None]:
    from pptx import Presentation

    prs = Presentation(str(pptx_path))
    return [s.shapes.title.text if s.shapes.title is not None else None for s in prs.slides]


def _three_slide_deck(tmp_path: Path, tools: dict[str, object]) -> None:
    content = "# Slide A\n- one\n---\n# Slide B\n- two\n---\n# Slide C\n- three\n"
    tools["write_pptx"](path="deck.pptx", content=content)


def test_delete_pptx_slide_removes_only_that_slide(tmp_path: Path) -> None:
    tools = _tools_by_name(tmp_path)
    _three_slide_deck(tmp_path, tools)

    result = tools["delete_pptx_slide"](path="deck.pptx", slide=2)
    assert result["deleted_slide"] == 2
    assert result["slide_count"] == 2
    assert _titles(tmp_path / "deck.pptx") == ["Slide A", "Slide C"]


def test_delete_pptx_slide_rejects_out_of_range(tmp_path: Path) -> None:
    tools = _tools_by_name(tmp_path)
    _three_slide_deck(tmp_path, tools)
    with pytest.raises(ValueError, match="out of range"):
        tools["delete_pptx_slide"](path="deck.pptx", slide=99)


def test_duplicate_pptx_slide_defaults_to_right_after_source(tmp_path: Path) -> None:
    tools = _tools_by_name(tmp_path)
    _three_slide_deck(tmp_path, tools)

    result = tools["duplicate_pptx_slide"](path="deck.pptx", slide=1)
    assert result["new_slide"] == 2
    assert result["slide_count"] == 4
    assert _titles(tmp_path / "deck.pptx") == ["Slide A", "Slide A", "Slide B", "Slide C"]


def test_duplicate_pptx_slide_honors_explicit_insert_at(tmp_path: Path) -> None:
    tools = _tools_by_name(tmp_path)
    _three_slide_deck(tmp_path, tools)

    tools["duplicate_pptx_slide"](path="deck.pptx", slide=1, insert_at=3)
    assert _titles(tmp_path / "deck.pptx") == ["Slide A", "Slide B", "Slide A", "Slide C"]


def test_duplicate_pptx_slide_can_insert_at_the_very_end(tmp_path: Path) -> None:
    tools = _tools_by_name(tmp_path)
    _three_slide_deck(tmp_path, tools)

    tools["duplicate_pptx_slide"](path="deck.pptx", slide=1, insert_at=4)
    assert _titles(tmp_path / "deck.pptx") == ["Slide A", "Slide B", "Slide C", "Slide A"]


def test_duplicate_pptx_slide_rejects_out_of_range_insert_at(tmp_path: Path) -> None:
    tools = _tools_by_name(tmp_path)
    _three_slide_deck(tmp_path, tools)
    with pytest.raises(ValueError, match="out of range"):
        tools["duplicate_pptx_slide"](path="deck.pptx", slide=1, insert_at=99)


def test_duplicate_pptx_slide_copies_shape_content_leaves_original_untouched(
    tmp_path: Path,
) -> None:
    """The copy must have the source's own body text (not just its
    title), and editing the copy afterward must not affect the
    original -- confirms it's a real independent XML part, not a shared
    reference."""
    from pptx import Presentation

    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- alpha\n- beta\n")

    tools["duplicate_pptx_slide"](path="deck.pptx", slide=1)
    tools["edit_pptx_text"](path="deck.pptx", slide=2, content="- CHANGED")

    prs = Presentation(str(tmp_path / "deck.pptx"))
    original_body = next(p for p in prs.slides[0].placeholders if p.placeholder_format.idx != 0)
    copy_body = next(p for p in prs.slides[1].placeholders if p.placeholder_format.idx != 0)
    assert "alpha" in original_body.text_frame.text
    assert "CHANGED" in copy_body.text_frame.text
    assert "alpha" not in copy_body.text_frame.text


def test_duplicate_pptx_slide_preserves_picture_and_hyperlink(tmp_path: Path) -> None:
    """Regression test for the real risk this tool's whole design is
    built around: relationship ids on the duplicated slide's own part
    are not guaranteed to match the source's, so every r:id-bearing
    attribute in the copied XML must be correctly remapped -- not just
    the common case where ids happen to line up. A picture (r:embed)
    and a hyperlink (r:id) are two different attribute names in two
    different elements, exercising the blanket remap generically rather
    than one specific tag."""
    from pptx import Presentation

    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- click me\n")
    _make_test_png(tmp_path / "logo.png")
    tools["add_pptx_image"](path="deck.pptx", slide=1, image_path="logo.png")

    prs = Presentation(str(tmp_path / "deck.pptx"))
    body = next(p for p in prs.slides[0].placeholders if p.placeholder_format.idx != 0)
    body.text_frame.paragraphs[0].runs[0].hyperlink.address = "https://example.com"
    prs.save(str(tmp_path / "deck.pptx"))

    tools["duplicate_pptx_slide"](path="deck.pptx", slide=1)

    prs2 = Presentation(str(tmp_path / "deck.pptx"))
    dup_slide = prs2.slides[1]
    pictures = [s for s in dup_slide.shapes if s.shape_type == 13]
    assert len(pictures) == 1
    assert pictures[0].image.size == (10, 10)
    dup_body = next(p for p in dup_slide.placeholders if p.placeholder_format.idx != 0)
    assert dup_body.text_frame.paragraphs[0].runs[0].hyperlink.address == "https://example.com"


def test_duplicate_pptx_slide_does_not_carry_over_speaker_notes(tmp_path: Path) -> None:
    """Documented v1 scope cut (see _duplicate_slide_part's docstring),
    not an accident -- pinned down as a test so a future change to this
    behavior is a deliberate decision, not a silent regression either
    way."""
    from pptx import Presentation

    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- bullet\n")
    tools["set_pptx_notes"](path="deck.pptx", slide=1, notes="speaker notes here")

    tools["duplicate_pptx_slide"](path="deck.pptx", slide=1)

    prs = Presentation(str(tmp_path / "deck.pptx"))
    dup_slide = prs.slides[1]
    assert dup_slide.has_notes_slide is False


def test_reorder_pptx_slide_moves_to_new_position(tmp_path: Path) -> None:
    tools = _tools_by_name(tmp_path)
    _three_slide_deck(tmp_path, tools)

    result = tools["reorder_pptx_slide"](path="deck.pptx", slide=3, new_position=1)
    assert result == {
        "path": "deck.pptx",
        "old_position": 3,
        "new_position": 1,
    }
    assert _titles(tmp_path / "deck.pptx") == ["Slide C", "Slide A", "Slide B"]


def test_reorder_pptx_slide_to_its_own_position_is_a_no_op(tmp_path: Path) -> None:
    tools = _tools_by_name(tmp_path)
    _three_slide_deck(tmp_path, tools)

    tools["reorder_pptx_slide"](path="deck.pptx", slide=2, new_position=2)
    assert _titles(tmp_path / "deck.pptx") == ["Slide A", "Slide B", "Slide C"]


def test_reorder_pptx_slide_rejects_out_of_range_new_position(tmp_path: Path) -> None:
    tools = _tools_by_name(tmp_path)
    _three_slide_deck(tmp_path, tools)
    with pytest.raises(ValueError, match="out of range"):
        tools["reorder_pptx_slide"](path="deck.pptx", slide=1, new_position=99)
