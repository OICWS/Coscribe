from pathlib import Path

import pytest

from .helpers import (
    _libreoffice_actually_works,
    _tools_by_name,
)


def test_add_pptx_hyperlink_whole_shape(tmp_path: Path) -> None:
    from pptx import Presentation

    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- body")

    result = tools["add_pptx_hyperlink"](
        path="deck.pptx", slide=1, shape_index=0, url="https://example.com"
    )
    assert result == {
        "path": "deck.pptx",
        "slide": 1,
        "shape_index": 0,
        "url": "https://example.com",
        "text": None,
    }

    prs = Presentation(tmp_path / "deck.pptx")
    shape = list(prs.slides[0].shapes)[0]
    assert shape.click_action.hyperlink.address == "https://example.com"


def test_add_pptx_hyperlink_on_one_run(tmp_path: Path) -> None:
    from pptx import Presentation

    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- one\n- two")

    result = tools["add_pptx_hyperlink"](
        path="deck.pptx", slide=1, shape_index=1, url="https://example.com/one", text="one"
    )
    assert result["text"] == "one"

    prs = Presentation(tmp_path / "deck.pptx")
    body = list(prs.slides[0].shapes)[1]
    runs = [run for p in body.text_frame.paragraphs for run in p.runs]
    linked = {run.text: run.hyperlink.address for run in runs}
    assert linked["one"] == "https://example.com/one"
    assert linked["two"] is None


def test_add_pptx_hyperlink_survives_round_trip(tmp_path: Path) -> None:
    import warnings

    from pptx import Presentation

    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- one")
    tools["add_pptx_hyperlink"](path="deck.pptx", slide=1, shape_index=0, url="https://example.com")

    with warnings.catch_warnings():
        warnings.simplefilter("error")
        prs = Presentation(str(tmp_path / "deck.pptx"))
    assert prs.slides[0].shapes[0].click_action.hyperlink.address == "https://example.com"


def test_list_pptx_shapes_reports_whole_shape_hyperlink(tmp_path: Path) -> None:
    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- body")
    tools["add_pptx_hyperlink"](path="deck.pptx", slide=1, shape_index=0, url="https://example.com")

    shapes = tools["list_pptx_shapes"](path="deck.pptx", slide=1)["shapes"]
    assert shapes[0]["hyperlink"] == "https://example.com"
    assert shapes[1]["hyperlink"] is None


def test_list_pptx_shapes_lists_a_group_shape_without_crashing(tmp_path: Path) -> None:
    from pptx import Presentation
    from pptx.util import Inches

    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- body")
    prs = Presentation(str(tmp_path / "deck.pptx"))
    group = prs.slides[0].shapes.add_group_shape()
    group.shapes.add_shape(1, Inches(1), Inches(1), Inches(1), Inches(1))
    prs.save(str(tmp_path / "deck.pptx"))

    shapes = tools["list_pptx_shapes"](path="deck.pptx", slide=1)["shapes"]

    # A group is one entry; its members are listed under it.
    groups = [shape for shape in shapes if shape["shape_type"] == "GROUP (6)"]
    assert len(groups) == 1
    assert groups[0]["hyperlink"] is None
    assert len(shapes) == len(Presentation(str(tmp_path / "deck.pptx")).slides[0].shapes)


def test_list_pptx_shapes_reports_slide_jump_hyperlink_in_the_same_url_syntax(
    tmp_path: Path,
) -> None:
    """Regression test for a real inconsistency: without this fix,
    list_pptx_shapes reported a slide-jump shape's hyperlink as the raw
    internal relationship target (e.g. "slide2.xml") instead of the
    "#slide-N" syntax add_pptx_hyperlink's own `url` parameter accepts --
    reading this field back and feeding it into another add_pptx_hyperlink
    call must round-trip, not require the model to somehow understand a
    raw part filename."""
    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# S1\n- a\n---\n# S2\n- b\n---\n# S3\n- c")
    tools["add_pptx_hyperlink"](path="deck.pptx", slide=1, shape_index=0, url="#slide-3")

    shapes = tools["list_pptx_shapes"](path="deck.pptx", slide=1)["shapes"]
    assert shapes[0]["hyperlink"] == "#slide-3"


def test_add_pptx_hyperlink_rejects_url_without_scheme(tmp_path: Path) -> None:
    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- body")

    with pytest.raises(ValueError, match="must start with one of"):
        tools["add_pptx_hyperlink"](path="deck.pptx", slide=1, shape_index=0, url="example.com")


def test_add_pptx_hyperlink_whole_shape_jumps_to_another_slide(tmp_path: Path) -> None:
    from pptx import Presentation

    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# S1\n- a\n---\n# S2\n- b\n---\n# S3\n- c")

    result = tools["add_pptx_hyperlink"](path="deck.pptx", slide=1, shape_index=0, url="#slide-3")
    assert result["url"] == "#slide-3"

    prs = Presentation(tmp_path / "deck.pptx")
    shape = prs.slides[0].shapes[0]
    assert prs.slides.index(shape.click_action.target_slide) == 2


def test_add_pptx_hyperlink_run_jumps_to_another_slide(tmp_path: Path) -> None:
    from pptx import Presentation
    from pptx.action import ActionSetting

    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# S1\n- a\n---\n# S2\n- b")

    tools["add_pptx_hyperlink"](path="deck.pptx", slide=1, shape_index=1, url="#slide-2", text="a")

    prs = Presentation(tmp_path / "deck.pptx")
    run = prs.slides[0].shapes[1].text_frame.paragraphs[0].runs[0]
    action = ActionSetting(run._r.get_or_add_rPr(), run)  # noqa: SLF001
    assert prs.slides.index(action.target_slide) == 1


def test_add_pptx_hyperlink_rejects_out_of_range_slide_target(tmp_path: Path) -> None:
    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# S1\n- a\n---\n# S2\n- b")

    with pytest.raises(ValueError, match="out of range -- deck has 2 slides"):
        tools["add_pptx_hyperlink"](path="deck.pptx", slide=1, shape_index=0, url="#slide-99")


def test_add_pptx_hyperlink_rejects_empty_url(tmp_path: Path) -> None:
    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- body")

    with pytest.raises(ValueError, match="must not be empty"):
        tools["add_pptx_hyperlink"](path="deck.pptx", slide=1, shape_index=0, url="   ")


def test_add_pptx_hyperlink_rejects_missing_run_text(tmp_path: Path) -> None:
    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- one\n- two")

    with pytest.raises(ValueError, match=r"no run with exact text 'nonexistent'"):
        tools["add_pptx_hyperlink"](
            path="deck.pptx",
            slide=1,
            shape_index=1,
            url="https://example.com",
            text="nonexistent",
        )


def test_add_pptx_hyperlink_rejects_text_on_shape_without_text_frame(tmp_path: Path) -> None:
    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# T\n| a | b |\n| - | - |\n| 1 | 2 |")

    with pytest.raises(ValueError, match="no text frame"):
        tools["add_pptx_hyperlink"](
            path="deck.pptx", slide=1, shape_index=1, url="https://example.com", text="a"
        )


def test_add_pptx_hyperlink_rejects_out_of_range_shape_index(tmp_path: Path) -> None:
    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- body")

    with pytest.raises(ValueError, match="2 shape"):
        tools["add_pptx_hyperlink"](
            path="deck.pptx", slide=1, shape_index=99, url="https://example.com"
        )


def test_add_pptx_hyperlink_out_of_range_slide_names_real_count(tmp_path: Path) -> None:
    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- body")

    with pytest.raises(ValueError, match="1 slides"):
        tools["add_pptx_hyperlink"](
            path="deck.pptx", slide=5, shape_index=0, url="https://example.com"
        )


def test_add_pptx_hyperlink_is_medium_risk_and_requires_approval(tmp_path: Path) -> None:
    from coscribe.runtime import get_tool_metadata

    tools = _tools_by_name(tmp_path)
    metadata = get_tool_metadata(tools["add_pptx_hyperlink"])
    assert metadata.risk_category == "WRITE_LOCAL"
    assert metadata.requires_approval is True


@pytest.mark.real_libreoffice
@pytest.mark.skipif(
    not _libreoffice_actually_works(),
    reason="LibreOffice not installed or not functional in this environment",
)
def test_add_pptx_hyperlink_slide_jump_survives_libreoffice_conversion(
    tmp_path: Path,
) -> None:
    """Can't verify the jump actually navigates in a static test (that
    needs a human clicking through a real slideshow), but a real
    subprocess conversion succeeding, plus a warnings-as-errors
    python-pptx round-trip, is the strongest automated check available --
    same discipline as every other hand-touched-XML feature in this file,
    even though this one is pure python-pptx public API under the hood."""
    import subprocess
    import warnings

    from pptx import Presentation

    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# S1\n- a\n---\n# S2\n- b\n---\n# S3\n- c")
    tools["add_pptx_hyperlink"](path="deck.pptx", slide=1, shape_index=0, url="#slide-3")
    tools["add_pptx_hyperlink"](path="deck.pptx", slide=1, shape_index=1, url="#slide-2", text="a")

    with warnings.catch_warnings():
        warnings.simplefilter("error")
        prs = Presentation(tmp_path / "deck.pptx")
        assert len(prs.slides) == 3

    result = subprocess.run(
        [
            "soffice",
            "--headless",
            "--convert-to",
            "pdf",
            "--outdir",
            str(tmp_path),
            str(tmp_path / "deck.pptx"),
        ],
        capture_output=True,
        timeout=30,
        check=True,
    )
    assert result.returncode == 0
    assert (tmp_path / "deck.pdf").is_file()
