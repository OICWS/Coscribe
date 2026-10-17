from pathlib import Path

import pytest

from tests.libreoffice_probe import convert_with_libreoffice

from .helpers import (
    _libreoffice_actually_works,
    _make_test_png,
    _tools_by_name,
)


def test_add_pptx_image_adds_a_picture_shape(tmp_path: Path) -> None:
    from pptx import Presentation

    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- body")
    _make_test_png(tmp_path / "logo.png")

    tools["add_pptx_image"](path="deck.pptx", slide=1, image_path="logo.png")

    prs = Presentation(tmp_path / "deck.pptx")
    pictures = [shape for shape in prs.slides[0].shapes if shape.shape_type == 13]
    assert len(pictures) == 1


def test_add_pptx_image_out_of_range_slide_names_real_count(tmp_path: Path) -> None:
    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- body")
    _make_test_png(tmp_path / "logo.png")

    with pytest.raises(ValueError, match="1 slides"):
        tools["add_pptx_image"](path="deck.pptx", slide=5, image_path="logo.png")


def test_add_pptx_image_on_missing_file_raises(tmp_path: Path) -> None:
    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- body")

    with pytest.raises(ValueError, match="does not exist"):
        tools["add_pptx_image"](path="deck.pptx", slide=1, image_path="missing.png")


def test_add_pptx_image_is_medium_risk_and_requires_approval(tmp_path: Path) -> None:
    from coscribe.runtime import get_tool_metadata

    tools = _tools_by_name(tmp_path)
    metadata = get_tool_metadata(tools["add_pptx_image"])
    assert metadata.risk_category == "WRITE_LOCAL"
    assert metadata.requires_approval is True


def _make_wide_test_png(path: Path) -> None:
    """A non-square image, wider than the default 4:3 slide's own ratio --
    needed to prove set_pptx_background_image's cover-crop math actually
    ran (crop fractions land on a non-default, non-trivial value), unlike
    _make_test_png's square image which a naive stretch-to-fill would also
    "cover" without any crop at all."""
    from PIL import Image

    Image.new("RGB", (400, 100), color="blue").save(path)


def test_set_pptx_background_image_places_picture_behind_existing_shapes(
    tmp_path: Path,
) -> None:
    from pptx import Presentation
    from pptx.oxml.ns import qn

    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- body")
    _make_wide_test_png(tmp_path / "bg.png")

    tools["set_pptx_background_image"](path="deck.pptx", slide=1, image_path="bg.png")

    prs = Presentation(tmp_path / "deck.pptx")
    sp_tree = prs.slides[0].shapes._spTree
    # First two children are always nvGrpSpPr/grpSpPr; the picture must be
    # the very next one (first *shape* child) so it renders behind the
    # title/body placeholders that were already on the slide.
    children = list(sp_tree)
    assert children[2].tag == qn("p:pic")
    assert all(child.tag != qn("p:pic") for child in children[3:])


def test_set_pptx_background_image_crops_to_cover_without_distortion(tmp_path: Path) -> None:
    from pptx import Presentation

    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- body")
    _make_wide_test_png(tmp_path / "bg.png")  # 400x100, much wider than a 4:3 slide

    tools["set_pptx_background_image"](path="deck.pptx", slide=1, image_path="bg.png")

    prs = Presentation(tmp_path / "deck.pptx")
    picture = next(shape for shape in prs.slides[0].shapes if shape.shape_type == 13)
    # Wider-than-slide image -> crop left/right, not top/bottom -- and the
    # crop must be a real, non-trivial fraction (not 0.0, which would mean
    # the cover-crop math never ran and the image was just stretched).
    assert picture.crop_left > 0.0
    assert picture.crop_right > 0.0
    assert picture.crop_top == 0.0
    assert picture.crop_bottom == 0.0
    # The shape itself still spans the whole slide -- the crop lives in
    # srcRect (which part of the source image is sampled), not the shape's
    # own on-slide extent.
    assert picture.width == prs.slide_width
    assert picture.height == prs.slide_height


def test_set_pptx_background_image_out_of_range_slide_names_real_count(tmp_path: Path) -> None:
    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- body")
    _make_wide_test_png(tmp_path / "bg.png")

    with pytest.raises(ValueError, match="1 slides"):
        tools["set_pptx_background_image"](path="deck.pptx", slide=5, image_path="bg.png")


def test_set_pptx_background_image_on_missing_file_raises(tmp_path: Path) -> None:
    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- body")

    with pytest.raises(ValueError, match="does not exist"):
        tools["set_pptx_background_image"](path="deck.pptx", slide=1, image_path="missing.png")


def test_set_pptx_background_image_is_medium_risk_and_requires_approval(tmp_path: Path) -> None:
    from coscribe.runtime import get_tool_metadata

    tools = _tools_by_name(tmp_path)
    metadata = get_tool_metadata(tools["set_pptx_background_image"])
    assert metadata.risk_category == "WRITE_LOCAL"
    assert metadata.requires_approval is True


@pytest.mark.real_libreoffice
@pytest.mark.skipif(not _libreoffice_actually_works(), reason="LibreOffice not usable here")
def test_set_pptx_background_image_survives_libreoffice_conversion(tmp_path: Path) -> None:
    """Real, non-mocked round trip -- catches OOXML corruption from the
    spTree element move that a pure structural check could miss."""

    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- body")
    _make_wide_test_png(tmp_path / "bg.png")
    tools["set_pptx_background_image"](path="deck.pptx", slide=1, image_path="bg.png")

    convert_with_libreoffice(tmp_path / "deck.pptx", tmp_path)
    assert (tmp_path / "deck.pdf").is_file()
    assert (tmp_path / "deck.pdf").stat().st_size > 0


def test_add_pptx_scrim_sets_alpha_on_the_fill(tmp_path: Path) -> None:
    from pptx import Presentation
    from pptx.oxml.ns import qn

    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- body")

    tools["add_pptx_scrim"](path="deck.pptx", slide=1, opacity=0.4, color="000000")

    prs = Presentation(tmp_path / "deck.pptx")
    rectangles = [shape for shape in prs.slides[0].shapes if shape.shape_type == 1]  # AUTO_SHAPE
    assert len(rectangles) == 1
    srgb_clr = rectangles[0].fill._xPr.find(qn("a:solidFill")).find(qn("a:srgbClr"))
    alpha = srgb_clr.find(qn("a:alpha"))
    assert alpha is not None
    assert alpha.get("val") == "40000"


def test_add_pptx_scrim_defaults_to_opacity_035(tmp_path: Path) -> None:
    from pptx import Presentation
    from pptx.oxml.ns import qn

    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- body")

    tools["add_pptx_scrim"](path="deck.pptx", slide=1)

    prs = Presentation(tmp_path / "deck.pptx")
    rectangle = next(shape for shape in prs.slides[0].shapes if shape.shape_type == 1)
    srgb_clr = rectangle.fill._xPr.find(qn("a:solidFill")).find(qn("a:srgbClr"))
    assert srgb_clr.find(qn("a:alpha")).get("val") == "35000"
    assert srgb_clr.get("val") == "000000"


def test_add_pptx_scrim_layers_above_background_picture_below_other_shapes(
    tmp_path: Path,
) -> None:
    from pptx import Presentation
    from pptx.oxml.ns import qn

    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- body")
    _make_wide_test_png(tmp_path / "bg.png")
    tools["set_pptx_background_image"](path="deck.pptx", slide=1, image_path="bg.png")

    tools["add_pptx_scrim"](path="deck.pptx", slide=1)

    prs = Presentation(tmp_path / "deck.pptx")
    sp_tree = prs.slides[0].shapes._spTree
    children = list(sp_tree)
    # Both the scrim and the title/body placeholders are <p:sp> elements --
    # a bare tag match can't tell them apart, so identify the scrim by the
    # one thing unique to it: an <a:alpha> element in its fill.
    alpha_path = ".//" + qn("a:alpha")
    pic_index = [c.tag for c in children].index(qn("p:pic"))
    scrim_index = next(i for i, c in enumerate(children) if c.find(alpha_path) is not None)
    assert scrim_index == pic_index + 1
    # Everything after the scrim is a plain <p:sp> without an alpha element
    # -- the original title/body placeholders, layered above the scrim.
    for element in children[scrim_index + 1 :]:
        assert element.find(alpha_path) is None


def test_add_pptx_scrim_without_background_picture_is_backmost(tmp_path: Path) -> None:
    from pptx import Presentation
    from pptx.oxml.ns import qn

    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- body")

    tools["add_pptx_scrim"](path="deck.pptx", slide=1)

    prs = Presentation(tmp_path / "deck.pptx")
    sp_tree = prs.slides[0].shapes._spTree
    children = list(sp_tree)
    group_props_index = [c.tag for c in children].index(qn("p:grpSpPr"))
    assert children[group_props_index + 1].tag == qn("p:sp")


def test_add_pptx_scrim_out_of_range_slide_names_real_count(tmp_path: Path) -> None:
    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- body")

    with pytest.raises(ValueError, match="1 slides"):
        tools["add_pptx_scrim"](path="deck.pptx", slide=5)


def test_add_pptx_scrim_is_medium_risk_and_requires_approval(tmp_path: Path) -> None:
    from coscribe.runtime import get_tool_metadata

    tools = _tools_by_name(tmp_path)
    metadata = get_tool_metadata(tools["add_pptx_scrim"])
    assert metadata.risk_category == "WRITE_LOCAL"
    assert metadata.requires_approval is True


@pytest.mark.real_libreoffice
@pytest.mark.skipif(not _libreoffice_actually_works(), reason="LibreOffice not usable here")
def test_add_pptx_scrim_survives_libreoffice_conversion(tmp_path: Path) -> None:
    """Real, non-mocked round trip -- catches OOXML corruption from the
    hand-appended <a:alpha> element and the spTree move that a pure
    structural check could miss."""

    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- body")
    _make_wide_test_png(tmp_path / "bg.png")
    tools["set_pptx_background_image"](path="deck.pptx", slide=1, image_path="bg.png")
    tools["add_pptx_scrim"](path="deck.pptx", slide=1, opacity=0.4)

    convert_with_libreoffice(tmp_path / "deck.pptx", tmp_path)
    assert (tmp_path / "deck.pdf").is_file()
    assert (tmp_path / "deck.pdf").stat().st_size > 0
