"""A section's line goes down to the right, or rises to the right with data-direction="up"; a
line may be flat (zero height or width)."""

from __future__ import annotations

import re
import zipfile
from pathlib import Path

from coscribe.tools.office.pptx.engine import build_deck


def _points(tmp_path: Path, attrs: str, style: str) -> list[tuple[int, int]]:
    pages = tmp_path / "pages"
    pages.mkdir()
    (pages / "01.html").write_text(
        f'<section><x-shape data-shape="line"{attrs} style="{style};border:4px solid #C2410C"/>'
        "</section>",
        encoding="utf-8",
    )
    report = build_deck(pages, tmp_path / "o.pptx", resource_root=tmp_path)
    assert report.ok, [e for page in report.pages for e in page.errors]
    with zipfile.ZipFile(tmp_path / "o.pptx") as pptx:
        xml = pptx.read("ppt/slides/slide1.xml").decode()
    return [(int(x), int(y)) for x, y in re.findall(r'<a:pt x="(\d+)" y="(\d+)"', xml)]


BOX = "left:200px;top:300px;width:400px;height:200px"


def test_a_line_goes_down_to_the_right_by_default(tmp_path: Path) -> None:
    (x1, y1), (x2, y2) = _points(tmp_path, "", BOX)[:2]
    assert x2 > x1 and y2 > y1


def test_a_line_that_rises_starts_low_and_ends_high(tmp_path: Path) -> None:
    (x1, y1), (x2, y2) = _points(tmp_path, ' data-direction="up"', BOX)[:2]
    assert x2 > x1 and y2 < y1


def test_a_flat_line_is_allowed_for_a_line_only(tmp_path: Path) -> None:
    (x1, y1), (x2, y2) = _points(tmp_path, "", "left:200px;top:300px;width:400px;height:0px")[:2]
    assert y1 == y2 and x2 > x1
    pages = tmp_path / "bad"
    pages.mkdir()
    (pages / "01.html").write_text(
        '<section><x-shape data-shape="rect" data-direction="up" style="left:0px;top:0px;'
        'width:100px;height:100px;background:#FF0000"/></section>',
        encoding="utf-8",
    )
    report = build_deck(pages, tmp_path / "bad.pptx", resource_root=tmp_path)
    assert not report.ok
    assert any("data-direction" in e for page in report.pages for e in page.errors)
