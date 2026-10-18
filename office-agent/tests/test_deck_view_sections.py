"""A slide section drawn as one SVG for the Slides panel (thumbnails, Present, downloads), in a
deck that mixes sections and SVG pages (decision 0016)."""

from __future__ import annotations

import re
from pathlib import Path

from PIL import Image

from coscribe.tools.office.pptx import deck_html, deck_pdf, read_deck, slide_svg
from coscribe.tools.office.pptx.engine import build_deck
from coscribe.tools.office.pptx.engine.text_layout import Font, Paragraph, Run, line_count, lines

from .test_deck_engine import COVER
from .test_deck_sections import SECTION
from .test_deck_sections_objects import CHART, TABLE


def _deck(tmp_path: Path, *slides: tuple[str, str]) -> Path:
    folder = tmp_path / "pages"
    (folder / "assets").mkdir(parents=True)
    Image.new("RGB", (96, 44), (30, 120, 200)).save(folder / "assets" / "photo.png")
    for name, text in slides:
        (folder / name).write_text(text, encoding="utf-8")
    assert build_deck(folder, tmp_path / "deck.pptx", resource_root=tmp_path).ok
    return tmp_path / "deck.pptx"


def _texts(svg: str) -> list[str]:
    """Each drawn line's words."""
    found = re.findall(r"<text\b[^>]*>(.*?)</text>", svg)
    return [re.sub(r"<[^>]+>", "", line) for line in found]


def test_a_section_is_drawn_with_its_text_shapes_and_picture(tmp_path: Path) -> None:
    deck = _deck(tmp_path, ("01.html", SECTION), ("02.svg", COVER))
    assert [s["kind"] for s in read_deck(deck)["slides"]] == ["section", "page"]
    svg = slide_svg(deck, 0, tmp_path)
    lines_drawn = _texts(svg)
    assert "第三季度经营回顾" in lines_drawn
    assert any("5,410 万元" in line for line in lines_drawn)
    assert "1." in lines_drawn and "2." in lines_drawn
    assert 'fill="#F7F5F0"' in svg and 'fill="#C2410C"' in svg
    assert 'href="data:image/png;base64,' in svg and "photo.png" not in svg
    # The embedded drawing, scaled into its box, and nothing of the notes.
    assert "scale(2)" in svg and "先讲收入" not in svg
    assert slide_svg(deck, 1, tmp_path).count("<svg") >= 1


def test_a_sections_chart_table_and_icon_are_drawn_as_built(tmp_path: Path) -> None:
    deck = _deck(tmp_path, ("01.html", TABLE), ("02.html", CHART))
    table = slide_svg(deck, 0, tmp_path)
    assert 'data-native="table"' in table and "合计" in table and "7,530" in table
    chart = slide_svg(deck, 1, tmp_path)
    assert 'data-native="chart"' in chart and "data-icon" not in chart and "metadata" not in chart


def test_long_text_wraps_inside_its_box(tmp_path: Path) -> None:
    words = "Revenue grew in every region this quarter " * 4
    section = (
        '<section><p id="title" style="left:100px;top:100px;width:600px;height:400px;'
        f'font-size:40px;text-align:center">{words.strip()}</p></section>'
    )
    svg = slide_svg(_deck(tmp_path, ("01.html", section)), 0, tmp_path)
    drawn = _texts(svg)
    assert len(drawn) > 2 and " ".join(drawn).split() == words.split()
    assert svg.count('text-anchor="middle"') == len(drawn)


def test_lines_break_where_the_box_height_was_measured() -> None:
    font = Font("Microsoft YaHei", 32.0)
    for text in ["收入同比增长，达到五千四百一十万元。" * 3, "word " * 30, "x" * 120]:
        paragraph = Paragraph([Run(text, font)], 32.0)
        broken = lines(paragraph, 500.0)
        assert len(broken) == line_count(paragraph, 500.0)
        assert "".join(t for line in broken for t, _run in line).replace(" ", "") == text.replace(
            " ", ""
        )


def test_downloads_take_a_deck_with_sections(tmp_path: Path) -> None:
    import pypdfium2

    deck = _deck(tmp_path, ("01.html", SECTION), ("02.html", TABLE), ("03.svg", COVER))
    assert len(pypdfium2.PdfDocument(deck_pdf(deck, tmp_path))) == 3
    assert deck_html(deck, tmp_path).count("data:image/svg+xml;base64,") == 3
