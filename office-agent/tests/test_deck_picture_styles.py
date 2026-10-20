"""A picture's border, rounded corners and opacity in a section (`<img style="border:...">`):
each reaches the picture in the built deck as its own geometry, outline and transparency, and the
picture drawn for the Slides panel shows the same."""

from __future__ import annotations

import re
import struct
import zipfile
import zlib
from pathlib import Path
from xml.etree import ElementTree as ET

from coscribe.tools.office.pptx.engine import build_deck
from coscribe.tools.office.pptx.engine.section_view import section_drawing

BOX = "left:100px;top:100px;width:400px;height:300px"


def _png(path: Path) -> None:
    def chunk(kind: bytes, data: bytes) -> bytes:
        body = struct.pack(">I", len(data)) + kind + data
        return body + struct.pack(">I", zlib.crc32(kind + data))

    rows = b"".join(b"\x00" + bytes([200, 30, 30]) * 40 for _ in range(30))
    path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", 40, 30, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(rows))
        + chunk(b"IEND", b"")
    )


def _slide_xml(tmp_path: Path, style: str) -> str:
    pages = tmp_path / "pages"
    pages.mkdir()
    _png(pages / "a.png")
    (pages / "01.html").write_text(
        f'<section><img src="a.png" style="{BOX};{style}"/></section>', encoding="utf-8"
    )
    report = build_deck(pages, tmp_path / "o.pptx", resource_root=tmp_path)
    assert report.ok, [e for page in report.pages for e in page.errors]
    with zipfile.ZipFile(tmp_path / "o.pptx") as pptx:
        return pptx.read("ppt/slides/slide1.xml").decode()


def test_a_plain_picture_has_no_outline_no_rounding_and_no_transparency(tmp_path: Path) -> None:
    xml = _slide_xml(tmp_path, "")
    assert '<a:prstGeom prst="rect">' in xml
    assert "<a:ln" not in xml and "alphaModFix" not in xml


def test_the_styles_reach_the_picture_in_the_deck(tmp_path: Path) -> None:
    xml = _slide_xml(tmp_path, "border-radius:40px;border:6px solid #112233;opacity:0.5")
    pic = re.search(r"<p:pic>.*</p:pic>", xml, re.S)
    assert pic is not None
    # 40px of a 300px side is 13333 of 100000; 6px is 38100 EMU; opacity 0.5 is 50000.
    assert 'prst="roundRect"' in pic[0] and 'fmla="val 13333"' in pic[0]
    assert '<a:ln w="38100">' in pic[0] and 'srgbClr val="112233"' in pic[0]
    assert '<a:alphaModFix amt="50000"/>' in pic[0]


def test_a_dashed_border_is_a_dashed_outline(tmp_path: Path) -> None:
    xml = _slide_xml(tmp_path, "border:4px dashed #112233")
    assert "<a:custDash>" in xml


def test_the_panels_picture_draws_the_border_over_the_rounded_picture() -> None:
    root = section_drawing(
        f'<section><img src="a.png" style="{BOX};border-radius:40px;border:6px solid #112233"/>'
        "</section>"
    )
    s = "{http://www.w3.org/2000/svg}"
    outline = [r for r in root.iter(f"{s}rect") if r.get("stroke")]
    assert len(outline) == 1
    assert outline[0].get("rx") == "40" and outline[0].get("stroke-width") == "6"
    assert outline[0].get("width") == "400" and outline[0].get("fill") == "none"
    assert ET.tostring(root, encoding="unicode").count("<image") == 1


def test_a_bad_border_is_refused_with_what_to_write(tmp_path: Path) -> None:
    pages = tmp_path / "pages"
    pages.mkdir()
    _png(pages / "a.png")
    (pages / "01.html").write_text(
        f'<section><img src="a.png" style="{BOX};border:thin dotted red"/></section>',
        encoding="utf-8",
    )
    report = build_deck(pages, tmp_path / "o.pptx", resource_root=tmp_path)
    assert not report.ok
    assert any("border is" in e for page in report.pages for e in page.errors)
