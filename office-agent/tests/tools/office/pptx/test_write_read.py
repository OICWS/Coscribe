import concurrent.futures
import shutil
from pathlib import Path

import pytest

from coscribe.tools.presentations import build_presentation_tools

from .helpers import (
    TWO_SLIDE_CONTENT,
    _libreoffice_actually_works,
    _tools_by_name,
)


def test_write_pptx_then_read_pptx_round_trips_title_and_bullets(tmp_path: Path) -> None:
    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# My Title\n- first\n- second")

    text = tools["read_pptx"](path="deck.pptx")

    assert "## My Title" in text
    assert "- first" in text
    assert "- second" in text


def test_pptx_edits_to_the_same_file_concurrently_do_not_corrupt_it(tmp_path: Path) -> None:
    """Same fix, same reasoning as spreadsheets_tool's identical
    concurrency regression test: any tool here that loads an existing
    .pptx, edits it, and saves it back (add_pptx_chart/set_pptx_notes/
    etc. -- unlike write_pptx itself, which always starts from a blank
    Presentation()) races if two calls target the same file at once,
    since LangGraph runs one AIMessage's tool_calls concurrently on
    separate threads. Fixed via tools/_file_locks.py's per-path lock
    (@locked_by_path); this drives 3 concurrent set_pptx_notes calls
    against 3 different slides of the same deck and asserts all 3
    notes survive with no corruption."""
    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](
        path="deck.pptx", content="# One\n- a\n\n---\n\n# Two\n- b\n\n---\n\n# Three\n- c"
    )

    def set_notes(slide: int) -> dict[str, object]:
        return tools["set_pptx_notes"](path="deck.pptx", slide=slide, notes=f"note-{slide}")  # type: ignore[operator]

    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        results = list(executor.map(set_notes, [1, 2, 3]))

    assert all("slide" in result for result in results)
    from pptx import Presentation

    prs = Presentation(str(tmp_path / "deck.pptx"))
    assert len(prs.slides) == 3
    notes = {slide.notes_slide.notes_text_frame.text for slide in prs.slides}
    assert notes == {"note-1", "note-2", "note-3"}


def test_write_pptx_default_canvas_is_real_16x9_widescreen(tmp_path: Path) -> None:
    from pptx import Presentation

    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- body")

    prs = Presentation(str(tmp_path / "deck.pptx"))
    assert (prs.slide_width, prs.slide_height) == (12192000, 6858000)


def test_write_pptx_default_canvas_title_placeholder_keeps_its_inherited_height(
    tmp_path: Path,
) -> None:
    # Live-reproduced defect: widening a stock layout's placeholder by
    # setting only .left/.width made python-pptx materialize a brand-new
    # <a:xfrm> with .top/.height defaulting to 0 (silently discarding the
    # values inherited from the slide master), rendering the title clipped
    # to a zero-height box. Both dimensions must survive intact.
    from pptx import Presentation

    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- body")

    prs = Presentation(str(tmp_path / "deck.pptx"))
    title = prs.slides[0].shapes.title
    assert title.top > 0
    assert title.height > 0


def test_write_pptx_bold_and_italic_markers_become_real_formatting(tmp_path: Path) -> None:
    from pptx import Presentation

    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](
        path="deck.pptx",
        content="# Title\nThis is **bold** and *italic* and plain text.",
    )

    prs = Presentation(str(tmp_path / "deck.pptx"))
    body_frame = prs.slides[0].placeholders[1].text_frame
    runs = body_frame.paragraphs[0].runs
    run_texts = [run.text for run in runs]

    assert "".join(run_texts) == "This is bold and italic and plain text."
    assert not any("*" in text for text in run_texts)
    bold_runs = [run for run in runs if run.font.bold]
    italic_runs = [run for run in runs if run.font.italic]
    assert [run.text for run in bold_runs] == ["bold"]
    assert [run.text for run in italic_runs] == ["italic"]


def test_multi_slide_round_trip_and_single_slide_read(tmp_path: Path) -> None:
    tools = _tools_by_name(tmp_path)
    result = tools["write_pptx"](path="deck.pptx", content=TWO_SLIDE_CONTENT)

    assert result["slide_count"] == 2

    full_text = tools["read_pptx"](path="deck.pptx")
    assert "## Intro" in full_text
    assert "## Data" in full_text
    assert "---" in full_text

    slide_two = tools["read_pptx"](path="deck.pptx", slide=2)
    assert "## Data" not in slide_two  # no heading prefix for a single-slide read
    assert "| Alice | 9 |" in slide_two
    assert "point one" not in slide_two


def test_table_only_slide_round_trips(tmp_path: Path) -> None:
    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](
        path="deck.pptx",
        content="# Data\n| a | b |\n| --- | --- |\n| 1 | 2 |",
    )

    text = tools["read_pptx"](path="deck.pptx")

    assert "| a | b |" in text
    assert "| 1 | 2 |" in text


def test_mixing_table_and_bullets_on_one_slide_raises(tmp_path: Path) -> None:
    tools = _tools_by_name(tmp_path)

    with pytest.raises(ValueError, match="table or bullets"):
        tools["write_pptx"](
            path="deck.pptx",
            content="# Mixed\n- a bullet\n| a | b |\n| --- | --- |\n| 1 | 2 |",
        )


def test_read_pptx_out_of_range_slide_names_real_count(tmp_path: Path) -> None:
    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content=TWO_SLIDE_CONTENT)

    with pytest.raises(ValueError, match="2 slides"):
        tools["read_pptx"](path="deck.pptx", slide=5)


def test_read_pptx_reads_text_inside_groups(tmp_path: Path) -> None:
    """A deck compiled from SVG keeps nearly all of its text in groups;
    read_pptx showed only the slide headings of one."""
    from pptx import Presentation
    from pptx.util import Inches

    prs = Presentation()
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    outer = slide.shapes.add_group_shape()
    box = (Inches(3), Inches(1))
    outer.shapes.add_textbox(Inches(1), Inches(1), *box).text = "净收入 2,345.79 万元"
    inner = outer.shapes.add_group_shape()
    inner.shapes.add_textbox(Inches(1), Inches(2), *box).text = "达成率 96.34%"
    slide.shapes.add_textbox(Inches(5), Inches(1), *box).text = "顶层文字"
    prs.save(str(tmp_path / "grouped.pptx"))
    tools = _tools_by_name(tmp_path)

    text = tools["read_pptx"](path="grouped.pptx", slide=1)

    assert text.splitlines() == ["- 净收入 2,345.79 万元", "- 达成率 96.34%", "- 顶层文字"]


def test_write_pptx_skips_qa_gracefully_when_soffice_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("shutil.which", lambda name: None)
    tools = _tools_by_name(tmp_path)

    result = tools["write_pptx"](path="deck.pptx", content="# Title\n- body")

    assert result["overflow_warnings"] == []
    assert result["qa_skipped_reason"]
    # The file itself still got written despite QA being unavailable.
    assert (tmp_path / "deck.pptx").is_file()


@pytest.mark.real_libreoffice
@pytest.mark.skipif(
    not _libreoffice_actually_works(),
    reason="LibreOffice not installed or not functional in this environment",
)
def test_write_pptx_detects_real_overflow_via_libreoffice(tmp_path: Path) -> None:
    tools = _tools_by_name(tmp_path)

    normal = tools["write_pptx"](path="normal.pptx", content="# Short\n- a short bullet")
    assert normal["overflow_warnings"] == []
    assert normal["qa_skipped_reason"] is None

    huge_bullet = " ".join(["overflow"] * 400)
    overflowing = tools["write_pptx"](
        path="overflowing.pptx", content=f"# Too Much\n- {huge_bullet}"
    )
    assert overflowing["overflow_warnings"] != []


def test_write_pptx_skips_preview_without_state_dir(tmp_path: Path) -> None:
    tools = _tools_by_name(tmp_path)  # no state_dir passed

    result = tools["write_pptx"](path="deck.pptx", content="# Title\n- body")

    assert result["preview_path"] is None
    assert result["preview_skipped_reason"] == "no state_dir configured"


@pytest.mark.real_libreoffice
@pytest.mark.skipif(
    not _libreoffice_actually_works(),
    reason="LibreOffice not installed or not functional in this environment",
)
def test_write_pptx_generates_real_preview_via_libreoffice(tmp_path: Path) -> None:
    state_dir = tmp_path / "state"
    tools = {
        tool.__name__: tool
        for tool in build_presentation_tools(tmp_path / "workspace", state_dir=state_dir)  # type: ignore[attr-defined]
    }

    result = tools["write_pptx"](path="deck.pptx", content="# Title\n- body")

    assert result["preview_skipped_reason"] is None
    preview_path = state_dir / "previews" / result["preview_path"]
    assert preview_path.is_file()
    assert preview_path.stat().st_size > 0


def test_render_pptx_preview_skips_gracefully_without_state_dir(tmp_path: Path) -> None:
    tools = _tools_by_name(tmp_path)  # no state_dir passed
    tools["write_pptx"](path="deck.pptx", content="# Title\n- body")

    result = tools["render_pptx_preview"](path="deck.pptx")

    assert result["preview_paths"] == []
    assert result["preview_paths_csv"] == ""
    assert result["preview_skipped_reason"] == "no state_dir configured"


@pytest.mark.real_libreoffice
@pytest.mark.skipif(
    not _libreoffice_actually_works(),
    reason="LibreOffice not installed/functional in this environment",
)
def test_render_pptx_preview_needs_no_poppler(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Pages are rasterized and measured by PDFium, not poppler: a Windows
    machine has LibreOffice at best, never pdftoppm."""
    state_dir = tmp_path / "state"
    tools = {
        tool.__name__: tool
        for tool in build_presentation_tools(tmp_path / "workspace", state_dir=state_dir)  # type: ignore[attr-defined]
    }
    tools["write_pptx"](path="deck.pptx", content="# Title\n- body")
    real_which = shutil.which
    monkeypatch.setattr(
        "shutil.which",
        lambda name, *a, **k: None if name in ("pdftoppm", "pdftotext") else real_which(name),
    )

    result = tools["render_pptx_preview"](path="deck.pptx")

    assert result["preview_skipped_reason"] is None
    assert len(result["preview_paths"]) >= 1


@pytest.mark.real_libreoffice
@pytest.mark.skipif(
    not _libreoffice_actually_works(),
    reason="LibreOffice not installed/functional in this environment",
)
def test_render_pptx_preview_renders_every_slide_via_libreoffice(tmp_path: Path) -> None:
    state_dir = tmp_path / "state"
    tools = {
        tool.__name__: tool
        for tool in build_presentation_tools(tmp_path / "workspace", state_dir=state_dir)  # type: ignore[attr-defined]
    }
    tools["write_pptx"](path="deck.pptx", content=TWO_SLIDE_CONTENT)

    result = tools["render_pptx_preview"](path="deck.pptx")

    assert result["preview_skipped_reason"] is None
    assert len(result["preview_paths"]) == 2
    assert result["preview_paths_csv"] == ",".join(result["preview_paths"])
    for name in result["preview_paths"]:
        preview_path = state_dir / "previews" / name
        assert preview_path.is_file()
        assert preview_path.stat().st_size > 0


def test_render_pptx_preview_flags_missing_visual_elements_without_state_dir_or_libreoffice(
    tmp_path: Path,
) -> None:
    # These two fields are pure python-pptx checks -- no soffice/pdftoppm
    # needed, so they must still come back even when preview rendering is
    # entirely skipped (no state_dir passed here at all).
    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- plain bullet, no visuals")

    result = tools["render_pptx_preview"](path="deck.pptx")

    assert result["preview_skipped_reason"] == "no state_dir configured"
    assert result["slides_missing_visual_elements"] == [1]
    assert result["text_overlap_warnings"] == []


def test_read_pptx_shows_a_charts_data_and_the_pictures(tmp_path: Path) -> None:
    from PIL import Image
    from pptx import Presentation
    from pptx.chart.data import CategoryChartData
    from pptx.enum.chart import XL_CHART_TYPE
    from pptx.util import Inches

    Image.new("RGB", (40, 20), "#336699").save(tmp_path / "photo.png")
    prs = Presentation()
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    data = CategoryChartData()
    data.categories = ["Q1", "Q2"]
    data.add_series("销售额", (1180, 1320.5))
    slide.shapes.add_chart(
        XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(1), Inches(1), Inches(4), Inches(3), data
    )
    slide.shapes.add_picture(str(tmp_path / "photo.png"), Inches(6), Inches(1), Inches(2))
    prs.save(str(tmp_path / "deck.pptx"))

    text = _tools_by_name(tmp_path)["read_pptx"](path="deck.pptx", slide=1)

    lines = text.splitlines()
    assert lines[:2] == ["[chart column_clustered]", "  销售额: Q1 1180, Q2 1320.5"]
    assert lines[2].startswith("[picture 'Picture 2', png, 192x96 px]")


def test_extra_writable_dir_lets_write_pptx_land_outside_workspace(tmp_path: Path) -> None:
    shared = tmp_path / "shared"
    shared.mkdir()
    workspace = tmp_path / "workspace"
    tools = {
        tool.__name__: tool
        for tool in build_presentation_tools(workspace, extra_writable=[shared])  # type: ignore[attr-defined]
    }

    tools["write_pptx"](path=str(shared / "deck.pptx"), content="# Title\n- body")

    text = tools["read_pptx"](path=str(shared / "deck.pptx"))
    assert "## Title" in text


def test_extra_readable_dir_rejects_write_pptx(tmp_path: Path) -> None:
    downloads = tmp_path / "downloads"
    downloads.mkdir()
    workspace = tmp_path / "workspace"
    tools = {
        tool.__name__: tool
        for tool in build_presentation_tools(workspace, extra_readable=[downloads])  # type: ignore[attr-defined]
    }

    with pytest.raises(PermissionError):
        tools["write_pptx"](path=str(downloads / "deck.pptx"), content="# Title\n- body")
