"""A deck built from pages on the user's own template: its layouts and theme carry over, a page
can start from an example slide's decoration, and the build tool describes the template first."""

from __future__ import annotations

import io
import zipfile
from pathlib import Path
from typing import Any

import pytest
from PIL import Image
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.util import Emu, Inches

from coscribe.tools.office.pptx.engine import compile_pages
from coscribe.tools.office.pptx.engine.template import describe
from coscribe.tools.office.pptx.engine.tool import build_engine_tools

_SVG = 'xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720" font-family="Microsoft YaHei"'


def _template(path: Path) -> None:
    """Two example slides: a cover with a navy panel and a logo, a content slide with a band."""
    prs = Presentation()
    prs.slide_width, prs.slide_height = Emu(12192000), Emu(6858000)
    cover = prs.slides.add_slide(prs.slide_layouts[0])
    panel = cover.shapes.add_shape(1, 0, 0, Emu(4572000), prs.slide_height)
    panel.name = "panel"
    panel.fill.solid()
    panel.fill.fore_color.rgb = RGBColor(0x1E, 0x27, 0x61)
    logo = io.BytesIO()
    Image.new("RGB", (40, 20), "#C2410C").save(logo, "PNG")
    cover.shapes.add_picture(logo, Inches(11), Inches(0.3), Inches(1), Inches(0.5)).name = "logo"
    content = prs.slides.add_slide(prs.slide_layouts[1])
    band = content.shapes.add_shape(1, 0, Emu(6720840), prs.slide_width, Emu(137160))
    band.name = "band"
    band.fill.solid()
    band.fill.fore_color.rgb = RGBColor(0x1E, 0x27, 0x61)
    prs.save(str(path))


def _page(root: str = "", body: str = "") -> str:
    title = '<text id="title" x="64" y="100" font-size="40">第三季度汇报</text>'
    return f"<svg {_SVG} {root}>{title}{body}</svg>"


def test_the_description_gives_canvas_theme_and_each_example_slides_decoration(
    tmp_path: Path,
) -> None:
    _template(tmp_path / "t.pptx")

    found = describe(tmp_path / "t.pptx")

    assert found["viewBox"] == "0 0 1280 720"
    assert found["colours"]["accent1"]  # type: ignore[index]
    cover, content = found["example_slides"]  # type: ignore[misc]
    assert cover["layout"] == "Title Slide"
    assert cover["decoration"][0] == {
        "kind": "shape",
        "x": 0,
        "y": 0,
        "width": 480,
        "height": 720,
        "fill": "#1E2761",
    }
    assert cover["decoration"][1]["kind"] == "picture"
    assert content["decoration"][0]["y"] == 706


def test_a_page_starts_from_an_example_slides_decoration(tmp_path: Path) -> None:
    _template(tmp_path / "t.pptx")
    out = tmp_path / "deck.pptx"

    report = compile_pages(
        [("cover", _page('data-template-slide="1"')), ("body", _page('data-template-slide="2"'))],
        out,
        template=tmp_path / "t.pptx",
    )

    assert report.ok, report.errors()
    cover, body = Presentation(str(out)).slides
    assert [s.name for s in cover.shapes] == ["panel", "logo", "title"]
    assert cover.slide_layout.name == "Title Slide"
    assert [s.name for s in body.shapes] == ["band", "title"]
    with zipfile.ZipFile(out) as package:
        assert len([n for n in package.namelist() if n.startswith("ppt/slides/slide")]) == 2
    logo = next(s for s in cover.shapes if s.name == "logo")
    assert Image.open(io.BytesIO(logo.image.blob)).getpixel((0, 0)) == (0xC2, 0x41, 0x0C)


def test_a_page_takes_a_layout_by_name_and_a_wrong_name_lists_them(tmp_path: Path) -> None:
    _template(tmp_path / "t.pptx")
    out = tmp_path / "deck.pptx"

    report = compile_pages(
        [("a", _page('data-layout="blank"')), ("b", _page('data-layout="Nope"'))],
        out,
        template=tmp_path / "t.pptx",
    )

    assert Presentation(str(out)).slides[0].slide_layout.name == "Blank"
    (error,) = report.errors()
    assert error.startswith('b: no layout named "Nope" in the template; it has "Title Slide"')


@pytest.mark.parametrize(
    ("root", "template", "message"),
    [
        ('data-template-slide="3"', True, "the template has 2 slides"),
        ('data-template-slide="1"', False, "needs a template"),
        ("4:3", True, "differs from the deck's 1280x720"),
    ],
)
def test_wrong_template_references_are_errors(
    tmp_path: Path, root: str, template: bool, message: str
) -> None:
    _template(tmp_path / "t.pptx")
    page = _page(root) if root != "4:3" else _page().replace("0 0 1280 720", "0 0 960 720")

    report = compile_pages(
        [("p", page)], tmp_path / "deck.pptx", template=tmp_path / "t.pptx" if template else None
    )

    assert any(message in error for error in report.errors()), report.errors()


def test_a_potx_template_is_read(tmp_path: Path) -> None:
    _template(tmp_path / "t.pptx")
    with (
        zipfile.ZipFile(tmp_path / "t.pptx") as source,
        zipfile.ZipFile(tmp_path / "t.potx", "w") as target,
    ):
        for item in source.infolist():
            data = source.read(item)
            if item.filename == "[Content_Types].xml":
                data = data.replace(b"presentation.main+xml", b"template.main+xml")
            target.writestr(item, data)

    assert len(describe(tmp_path / "t.potx")["example_slides"]) == 2  # type: ignore[arg-type]


def test_the_tool_describes_the_template_first_and_then_builds_on_it(tmp_path: Path) -> None:
    _template(tmp_path / "t.pptx")
    (tool,) = build_engine_tools(tmp_path)

    first: dict[str, Any] = tool("pages", "deck.pptx", template="t.pptx")
    (tmp_path / "pages").mkdir()
    (tmp_path / "pages" / "01.svg").write_text(_page('data-template-slide="2"'), encoding="utf-8")
    built: dict[str, Any] = tool("pages", "deck.pptx", template="t.pptx")

    assert first["template"]["viewBox"] == "0 0 1280 720"
    assert not (tmp_path / "deck.pptx").exists() or built
    assert built["ok"], built
    assert "band" in {s.name for s in Presentation(str(tmp_path / "deck.pptx")).slides[0].shapes}
