from pathlib import Path

import pytest

from .helpers import (
    _tools_by_name,
)


def test_edit_pptx_text_changes_title_and_content_leaving_the_rest_untouched(
    tmp_path: Path,
) -> None:
    from pptx import Presentation

    tools = _tools_by_name(tmp_path / "workspace")
    tools["write_pptx"](
        path="deck.pptx",
        content="# Slide One\n- original a\n- original b\n\n---\n\n# Slide Two\n- untouched",
    )

    tools["edit_pptx_text"](path="deck.pptx", slide=1, title="New Title", content="- new bullet")

    prs = Presentation(str(tmp_path / "workspace" / "deck.pptx"))
    slide1 = prs.slides[0]
    assert slide1.shapes.title.text == "New Title"
    body = next(
        p
        for p in slide1.placeholders
        if p.placeholder_format.idx != slide1.shapes.title.placeholder_format.idx
    )
    assert [p.text for p in body.text_frame.paragraphs] == ["new bullet"]
    # Slide 2 (not addressed by this call) is exactly as write_pptx left it.
    slide2 = prs.slides[1]
    assert slide2.shapes.title.text == "Slide Two"


def test_edit_pptx_text_title_only_leaves_existing_content_placeholder_alone(
    tmp_path: Path,
) -> None:
    from pptx import Presentation

    tools = _tools_by_name(tmp_path / "workspace")
    tools["write_pptx"](path="deck.pptx", content="# Old Title\n- keep me")

    tools["edit_pptx_text"](path="deck.pptx", slide=1, title="Renamed")

    prs = Presentation(str(tmp_path / "workspace" / "deck.pptx"))
    slide = prs.slides[0]
    assert slide.shapes.title.text == "Renamed"
    body = next(
        p
        for p in slide.placeholders
        if p.placeholder_format.idx != slide.shapes.title.placeholder_format.idx
    )
    assert body.text_frame.text == "keep me"


def test_edit_pptx_text_content_only_leaves_existing_title_alone(tmp_path: Path) -> None:
    from pptx import Presentation

    tools = _tools_by_name(tmp_path / "workspace")
    tools["write_pptx"](path="deck.pptx", content="# Keep Me\n- old bullet")

    tools["edit_pptx_text"](path="deck.pptx", slide=1, content="- replaced bullet")

    prs = Presentation(str(tmp_path / "workspace" / "deck.pptx"))
    slide = prs.slides[0]
    assert slide.shapes.title.text == "Keep Me"
    body = next(
        p
        for p in slide.placeholders
        if p.placeholder_format.idx != slide.shapes.title.placeholder_format.idx
    )
    assert body.text_frame.text == "replaced bullet"


def test_edit_pptx_text_neither_title_nor_content_raises(tmp_path: Path) -> None:
    tools = _tools_by_name(tmp_path / "workspace")
    tools["write_pptx"](path="deck.pptx", content="# Title\n- x")

    with pytest.raises(ValueError, match="needs title and/or content, or find"):
        tools["edit_pptx_text"](path="deck.pptx", slide=1)


def test_edit_pptx_text_title_on_slide_with_no_title_placeholder_raises(
    tmp_path: Path,
) -> None:
    tools = _tools_by_name(tmp_path / "workspace")
    # A table-only slide chunk still gets a title placeholder from
    # _TITLE_ONLY_LAYOUT in this codebase's write_pptx, so build a slide
    # with none the same way _make_fake_template's "Blank" layout does.
    from pptx import Presentation

    prs = Presentation()
    prs.slides.add_slide(prs.slide_layouts[6])  # "Blank" -- no placeholders at all
    (tmp_path / "workspace").mkdir(parents=True, exist_ok=True)
    prs.save(str(tmp_path / "workspace" / "blank.pptx"))

    with pytest.raises(ValueError, match="no title placeholder"):
        tools["edit_pptx_text"](path="blank.pptx", slide=1, title="New Title")


def test_edit_pptx_text_rejects_a_table_in_content(tmp_path: Path) -> None:
    tools = _tools_by_name(tmp_path / "workspace")
    tools["write_pptx"](path="deck.pptx", content="# Title\n- x")

    with pytest.raises(ValueError, match="doesn't support tables"):
        tools["edit_pptx_text"](
            path="deck.pptx", slide=1, content="| a | b |\n| --- | --- |\n| 1 | 2 |"
        )


def test_edit_pptx_text_out_of_range_placeholder_index_raises(tmp_path: Path) -> None:
    tools = _tools_by_name(tmp_path / "workspace")
    tools["write_pptx"](path="deck.pptx", content="# Title\n- x")

    with pytest.raises(ValueError, match="placeholder_index=1"):
        tools["edit_pptx_text"](path="deck.pptx", slide=1, content="- y", placeholder_index=1)


def test_edit_pptx_text_placeholder_index_reaches_the_second_content_placeholder(
    tmp_path: Path,
) -> None:
    """Regression coverage for the real gap fill_pptx_template still has
    (see its own tests/docstring): a "two column" slide has two
    independent content placeholders, and placeholder_index lets
    edit_pptx_text address the second one specifically -- verified live
    against a real Microsoft-authored template's identical layout shape."""
    from pptx import Presentation

    tools = _tools_by_name(tmp_path / "workspace")
    tools["write_pptx"](
        path="deck.pptx",
        content="layout: two-column\n# Two Columns\n- left one\n\n>>>\n\n- right one",
    )

    tools["edit_pptx_text"](
        path="deck.pptx", slide=1, content="- left replaced", placeholder_index=0
    )
    tools["edit_pptx_text"](
        path="deck.pptx", slide=1, content="- right replaced", placeholder_index=1
    )

    prs = Presentation(str(tmp_path / "workspace" / "deck.pptx"))
    slide = prs.slides[0]
    bodies = [
        p
        for p in slide.placeholders
        if p.placeholder_format.idx != slide.shapes.title.placeholder_format.idx
    ]
    assert [p.text_frame.text for p in bodies] == ["left replaced", "right replaced"]


def test_edit_pptx_text_is_write_local_and_requires_approval(tmp_path: Path) -> None:
    from coscribe.runtime import get_tool_metadata

    tools = _tools_by_name(tmp_path / "workspace")
    metadata = get_tool_metadata(tools["edit_pptx_text"])  # type: ignore[arg-type]
    assert metadata.risk_category == "WRITE_LOCAL"
    assert metadata.requires_approval is True
