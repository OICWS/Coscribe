"""Shapes made to look like another, as PowerPoint's Format Painter does: the parts named are
copied exactly, and the targets' text, position and the rest of the slide stay as they were."""

from __future__ import annotations

from pathlib import Path

import pytest
from lxml import etree
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Cm, Pt

from coscribe.tools.office.pptx.toolkit import PresentationToolkit


def _deck(path: Path) -> None:
    deck = Presentation()
    slide = deck.slides.add_slide(deck.slide_layouts[6])
    model = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Cm(1), Cm(1), Cm(5), Cm(2))
    model.adjustments[0] = 0.3
    model.fill.solid()
    model.fill.fore_color.rgb = RGBColor(0xDD, 0xE9, 0xFF)
    model.line.color.rgb = RGBColor(0x37, 0x68, 0xB3)
    model.line.width = Pt(1.3)
    model.text_frame.text = "Model"
    model.text_frame.vertical_anchor = MSO_ANCHOR.MIDDLE
    model.text_frame.paragraphs[0].alignment = PP_ALIGN.CENTER
    font = model.text_frame.paragraphs[0].runs[0].font
    font.size, font.bold, font.name = Pt(13), True, "Noto Sans"
    font.color.rgb = RGBColor(0x10, 0x20, 0x30)
    for left, text in ((8, "First line\nsecond line"), (15, "Other")):
        box = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Cm(left), Cm(4), Cm(3), Cm(3))
        box.text_frame.text = text
        box.text_frame.paragraphs[0].runs[0].font.size = Pt(20)
    slide.shapes.add_textbox(Cm(1), Cm(10), Cm(5), Cm(1)).text_frame.text = "Untouched"
    deck.save(str(path))


def test_targets_take_the_source_look_and_keep_their_text_and_place(tmp_path: Path):
    _deck(tmp_path / "d.pptx")
    before = Presentation(str(tmp_path / "d.pptx")).slides[0].shapes[3]._element

    result = PresentationToolkit(tmp_path).match_pptx_shape_format("d.pptx", 1, "0", ["1", "2"])

    assert result["copied"] == ["size", "shape", "fill", "line", "text"]
    shapes = Presentation(str(tmp_path / "d.pptx")).slides[0].shapes
    for box in (shapes[1], shapes[2]):
        assert (box.width, box.height) == (Cm(5), Cm(2))
        assert box.auto_shape_type == MSO_SHAPE.ROUNDED_RECTANGLE
        assert box.adjustments[0] == pytest.approx(0.3)
        assert box.fill.fore_color.rgb == RGBColor(0xDD, 0xE9, 0xFF)
        assert box.line.color.rgb == RGBColor(0x37, 0x68, 0xB3) and box.line.width == Pt(1.3)
        assert box.text_frame.vertical_anchor == MSO_ANCHOR.MIDDLE
        for paragraph in box.text_frame.paragraphs:
            assert paragraph.alignment == PP_ALIGN.CENTER
            for run in paragraph.runs:
                assert (run.font.size, run.font.bold, run.font.name) == (Pt(13), True, "Noto Sans")
                assert run.font.color.rgb == RGBColor(0x10, 0x20, 0x30)
    assert shapes[1].text_frame.text == "First line\nsecond line"
    assert (shapes[1].left, shapes[1].top) == (Cm(8), Cm(4))
    assert etree.tostring(shapes[3]._element) == etree.tostring(before)
    assert shapes[0].text_frame.text == "Model"


def test_only_the_named_parts_are_copied(tmp_path: Path):
    _deck(tmp_path / "d.pptx")

    PresentationToolkit(tmp_path).match_pptx_shape_format("d.pptx", 1, "0", ["2"], ["fill"])

    box = Presentation(str(tmp_path / "d.pptx")).slides[0].shapes[2]
    assert box.fill.fore_color.rgb == RGBColor(0xDD, 0xE9, 0xFF)
    assert (box.width, box.auto_shape_type) == (Cm(3), MSO_SHAPE.RECTANGLE)
    assert box.text_frame.paragraphs[0].runs[0].font.size == Pt(20)


@pytest.mark.parametrize(
    ("targets", "parts", "message"),
    [
        ([], None, "at least one target"),
        (["1"], ["colour"], "not among"),
        (["0", "1"], None, "source is among the targets"),
    ],
)
def test_a_request_that_names_nothing_to_do_is_refused(
    tmp_path: Path, targets: list[str], parts: list[str] | None, message: str
):
    _deck(tmp_path / "d.pptx")
    before = (tmp_path / "d.pptx").read_bytes()
    with pytest.raises(ValueError, match=message):
        PresentationToolkit(tmp_path).match_pptx_shape_format("d.pptx", 1, "0", targets, parts)
    assert (tmp_path / "d.pptx").read_bytes() == before
