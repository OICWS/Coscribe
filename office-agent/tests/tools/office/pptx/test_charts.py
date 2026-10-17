from pathlib import Path

import pytest

from coscribe.tools.office.pptx.qa import (
    check_text_overlaps,
)

from .helpers import (
    _tools_by_name,
)

CHART_TABLE = """\
| Quarter | Revenue | Profit |
| --- | --- | --- |
| Q1 | 100 | 20 |
| Q2 | 120 | 25 |
"""


def test_add_pptx_chart_adds_a_chart_of_the_right_type(tmp_path: Path) -> None:
    from pptx import Presentation
    from pptx.enum.chart import XL_CHART_TYPE

    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- body")

    tools["add_pptx_chart"](
        path="deck.pptx", slide=1, chart_type="bar", data=CHART_TABLE, title="Q1 vs Q2"
    )

    prs = Presentation(tmp_path / "deck.pptx")
    charts = [shape for shape in prs.slides[0].shapes if shape.has_chart]
    assert len(charts) == 1
    assert charts[0].chart.chart_type == XL_CHART_TYPE.COLUMN_CLUSTERED


def test_add_pptx_chart_rejects_unknown_chart_type(tmp_path: Path) -> None:
    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- body")

    with pytest.raises(ValueError, match="Unknown chart_type"):
        tools["add_pptx_chart"](path="deck.pptx", slide=1, chart_type="scatter", data=CHART_TABLE)


def test_add_pptx_chart_rejects_non_table_data(tmp_path: Path) -> None:
    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- body")

    with pytest.raises(ValueError, match="pipe-table"):
        tools["add_pptx_chart"](path="deck.pptx", slide=1, chart_type="bar", data="not a table")


def test_add_pptx_chart_rejects_non_numeric_cell(tmp_path: Path) -> None:
    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- body")

    bad_table = "| Quarter | Revenue |\n| --- | --- |\n| Q1 | not-a-number |"
    with pytest.raises(ValueError, match="not numeric"):
        tools["add_pptx_chart"](path="deck.pptx", slide=1, chart_type="bar", data=bad_table)


def test_add_pptx_chart_rejects_multi_series_pie_chart(tmp_path: Path) -> None:
    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- body")

    with pytest.raises(ValueError, match="pie"):
        tools["add_pptx_chart"](path="deck.pptx", slide=1, chart_type="pie", data=CHART_TABLE)


def test_add_pptx_chart_out_of_range_slide_names_real_count(tmp_path: Path) -> None:
    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- body")

    with pytest.raises(ValueError, match="1 slides"):
        tools["add_pptx_chart"](path="deck.pptx", slide=5, chart_type="bar", data=CHART_TABLE)


def test_add_pptx_chart_on_missing_file_raises(tmp_path: Path) -> None:
    tools = _tools_by_name(tmp_path)

    with pytest.raises(ValueError, match="does not exist"):
        tools["add_pptx_chart"](path="missing.pptx", slide=1, chart_type="bar", data=CHART_TABLE)


def test_add_pptx_chart_is_medium_risk_and_requires_approval(tmp_path: Path) -> None:
    from coscribe.runtime import get_tool_metadata

    tools = _tools_by_name(tmp_path)
    metadata = get_tool_metadata(tools["add_pptx_chart"])
    assert metadata.risk_category == "WRITE_LOCAL"
    assert metadata.requires_approval is True


def test_add_pptx_chart_positions_below_existing_body_text_without_overlap(
    tmp_path: Path,
) -> None:
    """Real, live-reproduced bug: the old fixed Inches(1, 1.6, 8, 5) chart
    box landed directly on top of a slide's own short intro sentence.
    A chart added next to real body text must not overlap it, and must
    stay within the slide's own real bounds -- not just some fraction of
    an unrelated content-area constant (the second bug the first fix's
    naive version introduced, see the git history for this test)."""
    from pptx import Presentation

    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Revenue Trend\n- One short intro line")

    tools["add_pptx_chart"](path="deck.pptx", slide=1, chart_type="line", data=CHART_TABLE)

    prs = Presentation(tmp_path / "deck.pptx")
    slide = prs.slides[0]
    body = next(
        s
        for s in slide.shapes
        if s.has_text_frame and "intro line" in s.text_frame.text and not s.has_chart
    )
    chart_shape = next(s for s in slide.shapes if s.has_chart)
    assert chart_shape.top >= body.top + body.height
    assert chart_shape.top + chart_shape.height <= (prs.slide_height or 0)
    assert check_text_overlaps(prs) == []
    # Real, live-reproduced defect this last assertion catches: shrinking
    # the body placeholder by setting only `.height` (before this was
    # fixed to set left/top/width too) made python-pptx create a bare new
    # <a:xfrm> with width defaulting to 0 -- the placeholder rendered as
    # a near-zero-width sliver, one character per line, spilling off the
    # slide. A 0-width bbox still "has" a bbox, so no automated overlap/
    # missing-visual check catches this on its own; only a direct width
    # assertion does.
    assert body.width > 0


def test_add_pptx_chart_rejects_when_body_text_leaves_no_room(tmp_path: Path) -> None:
    tools = _tools_by_name(tmp_path)
    many_bullets = "\n".join(f"- point number {i}" for i in range(20))
    tools["write_pptx"](path="deck.pptx", content=f"# Busy Slide\n{many_bullets}")

    with pytest.raises(ValueError, match="too little room"):
        tools["add_pptx_chart"](path="deck.pptx", slide=1, chart_type="line", data=CHART_TABLE)


def test_add_pptx_chart_font_color_matches_default_black_theme(tmp_path: Path) -> None:
    from pptx import Presentation
    from pptx.dml.color import RGBColor

    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- body")

    tools["add_pptx_chart"](path="deck.pptx", slide=1, chart_type="bar", data=CHART_TABLE)

    prs = Presentation(tmp_path / "deck.pptx")
    chart = next(s for s in prs.slides[0].shapes if s.has_chart).chart
    assert chart.font.color.rgb == RGBColor(0x00, 0x00, 0x00)  # type: ignore[no-untyped-call]


def test_add_pptx_chart_font_color_matches_custom_dark_theme(tmp_path: Path) -> None:
    """Real, live-reproduced bug: a chart's axis/legend text stayed black
    (python-pptx's own chart default) even on a deck whose `theme=`
    parameter lightened every other piece of text on the slide, making it
    unreadable against a dark background."""
    from pptx import Presentation
    from pptx.dml.color import RGBColor

    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- body", theme="bg=111827,text=F8FAFC")

    tools["add_pptx_chart"](path="deck.pptx", slide=1, chart_type="bar", data=CHART_TABLE)

    prs = Presentation(tmp_path / "deck.pptx")
    chart = next(s for s in prs.slides[0].shapes if s.has_chart).chart
    assert chart.font.color.rgb == RGBColor.from_string("F8FAFC")  # type: ignore[no-untyped-call]
