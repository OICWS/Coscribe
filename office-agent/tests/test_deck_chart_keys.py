"""The chart keys the Slides panel writes (`frontend/src/lib/slideChart.ts`) reach the native
PowerPoint chart, so a control in the panel never changes only the picture of it."""

from __future__ import annotations

import json
import re
import zipfile
from pathlib import Path

from coscribe.tools.office.pptx.engine import compile_sections

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
