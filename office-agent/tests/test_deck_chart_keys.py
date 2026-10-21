"""The chart keys the Slides panel writes (`frontend/src/lib/slideChart.ts`) reach the native
PowerPoint chart, so a control in the panel never changes only the picture of it."""

from __future__ import annotations

import json
import re
import zipfile
from pathlib import Path

from coscribe.tools.office.pptx import slide_svg
from coscribe.tools.office.pptx.engine import build_deck, compile_sections

BASE = {
    "type": "column",
    "categories": ["A", "B", "C"],
    "series": [{"name": "S1", "values": [3, 5, 2]}, {"name": "S2", "values": [1, 4, 6]}],
    "font_size": 27,
}


def _chart_xml(tmp_path: Path, **extra: object) -> str:
    spec = json.dumps({**BASE, **extra})
    source = (
        '<section><x-chart id="c" style="left:96px;top:200px;width:900px;height:600px">'
        f"{spec}</x-chart></section>"
    )
    report = compile_sections([("01.html", source)], tmp_path / "o.pptx", resource_root=tmp_path)
    assert report.ok, [e for page in report.pages for e in page.errors]
    with zipfile.ZipFile(tmp_path / "o.pptx") as pptx:
        name = next(n for n in pptx.namelist() if re.fullmatch(r"ppt/charts/chart\d*\.xml", n))
        return pptx.read(name).decode()


def test_the_panels_chart_keys_are_written_into_the_chart(tmp_path: Path) -> None:
    plain = _chart_xml(tmp_path)
    assert "<c:legend>" not in plain and "<c:dLbls>" not in plain
    assert '<c:barDir val="col"' in plain and '<c:grouping val="clustered"' in plain

    xml = _chart_xml(
        tmp_path,
        show_legend=True,
        data_labels=True,
        title="Revenue",
        grouping="stacked",
        style={"colors": ["#C2410C", "#0E3A66"]},
    )
    assert "<c:legend>" in xml and "<c:dLbls>" in xml
    assert "Revenue" in xml and '<c:grouping val="stacked"' in xml
    assert 'srgbClr val="C2410C"' in xml and 'srgbClr val="0E3A66"' in xml


def test_the_panels_chart_types_become_the_matching_chart(tmp_path: Path) -> None:
    for chart_type, element in (("bar", "barChart"), ("line", "lineChart"), ("area", "areaChart")):
        assert f"<c:{element}>" in _chart_xml(tmp_path, type=chart_type)
    assert '<c:barDir val="bar"' in _chart_xml(tmp_path, type="bar")


def test_the_panels_axis_keys_are_written_into_the_chart(tmp_path: Path) -> None:
    xml = _chart_xml(
        tmp_path,
        axis_titles={"category": "Region", "value": "Revenue"},
        axes={"value": {"minimum": 0, "maximum": 100, "number_format": "0%"}},
    )
    assert "Region" in xml and "Revenue" in xml
    assert '<c:max val="100"' in xml and '<c:min val="0"' in xml and 'formatCode="0%"' in xml


def test_a_text_boxs_shadow_is_its_own_effect_and_is_drawn(tmp_path: Path) -> None:
    source = (
        '<section><p id="t" style="left:96px;top:200px;width:900px;height:200px;font-size:40px;'
        'box-shadow:0px 6px 12px #112233 0.4">Quiet</p></section>'
    )
    out = tmp_path / "o.pptx"
    folder = tmp_path / "pages"
    folder.mkdir()
    (folder / "01.html").write_text(source, encoding="utf-8")
    assert build_deck(folder, out, resource_root=tmp_path).ok
    with zipfile.ZipFile(out) as pptx:
        slide = pptx.read("ppt/slides/slide1.xml").decode()
    assert "<a:outerShdw" in slide and 'val="112233"' in slide and 'dir="5400000"' in slide
    assert "feDropShadow" in slide_svg(out, 0, tmp_path)
