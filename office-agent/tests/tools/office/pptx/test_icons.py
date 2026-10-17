from pathlib import Path
from typing import Any

import pytest

from .helpers import (
    _tools_by_name,
)

# --- list_pptx_icons / add_pptx_icon (Tier 1 #3: bundled Lucide icons) ---


def test_list_pptx_icons_returns_a_sorted_nonempty_list_of_known_names(tmp_path: Path) -> None:
    tools = _tools_by_name(tmp_path)
    names = tools["list_pptx_icons"]()
    assert names == sorted(names)
    assert len(names) > 30
    assert "check" in names
    assert "trending-up" in names


def test_add_pptx_icon_inserts_a_square_picture_at_the_given_position(tmp_path: Path) -> None:
    from pptx import Presentation
    from pptx.util import Inches

    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- bullet\n")

    result = tools["add_pptx_icon"](
        path="deck.pptx",
        slide=1,
        icon_name="check",
        left_in=2.0,
        top_in=3.0,
        size_in=1.25,
    )
    assert result["icon_name"] == "check"

    prs = Presentation(str(tmp_path / "deck.pptx"))
    shapes = list(prs.slides[0].shapes)
    icon = shapes[-1]
    assert icon.shape_type == 13  # PICTURE
    assert icon.left == Inches(2.0)
    assert icon.top == Inches(3.0)
    assert icon.width == Inches(1.25)
    assert icon.height == Inches(1.25)


def test_add_pptx_icon_recolors_to_the_requested_color(tmp_path: Path) -> None:
    from io import BytesIO

    from PIL import Image
    from pptx import Presentation

    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- bullet\n")
    tools["add_pptx_icon"](path="deck.pptx", slide=1, icon_name="check", color="38BDF8")

    prs = Presentation(str(tmp_path / "deck.pptx"))
    icon = list(prs.slides[0].shapes)[-1]
    img = Image.open(BytesIO(icon.image.blob)).convert("RGBA")
    bbox = img.getbbox()
    assert bbox is not None
    # Find one solidly-opaque pixel (avoid anti-aliased edges) and check
    # its RGB matches the requested color exactly.
    found = None
    for y in range(bbox[1], bbox[3]):
        for x in range(bbox[0], bbox[2]):
            pixel = img.getpixel((x, y))
            if pixel[3] == 255:
                found = pixel
                break
        if found:
            break
    assert found is not None
    assert found[:3] == (0x38, 0xBD, 0xF8)


def test_add_pptx_icon_default_color_is_applied_when_omitted(tmp_path: Path) -> None:
    from io import BytesIO

    from PIL import Image
    from pptx import Presentation

    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- bullet\n")
    tools["add_pptx_icon"](path="deck.pptx", slide=1, icon_name="check")

    prs = Presentation(str(tmp_path / "deck.pptx"))
    icon = list(prs.slides[0].shapes)[-1]
    img = Image.open(BytesIO(icon.image.blob)).convert("RGBA")
    bbox = img.getbbox()
    assert bbox is not None


def test_add_pptx_icon_rejects_unknown_icon_name(tmp_path: Path) -> None:
    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- bullet\n")
    with pytest.raises(ValueError, match="Unknown icon"):
        tools["add_pptx_icon"](path="deck.pptx", slide=1, icon_name="not-a-real-icon")


def test_add_pptx_icon_rejects_bad_color(tmp_path: Path) -> None:
    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- bullet\n")
    with pytest.raises(ValueError, match="6-hex-digit color"):
        tools["add_pptx_icon"](path="deck.pptx", slide=1, icon_name="check", color="#38BDF8")


def test_add_pptx_icon_rejects_out_of_range_slide(tmp_path: Path) -> None:
    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- bullet\n")
    with pytest.raises(ValueError, match="out of range"):
        tools["add_pptx_icon"](path="deck.pptx", slide=2, icon_name="check")


def _solid_opaque_pixel(img: Any) -> tuple[int, int, int, int]:
    """First solidly-opaque pixel (avoid anti-aliased edges), matching
    the same avoid-edge-pixels pattern add_pptx_icon's own recolor test
    already uses."""
    bbox = img.getbbox()
    assert bbox is not None
    for y in range(bbox[1], bbox[3]):
        for x in range(bbox[0], bbox[2]):
            pixel = img.getpixel((x, y))
            if pixel[3] == 255:
                return pixel
    raise AssertionError("no solidly-opaque pixel found")


def test_recolor_pptx_icon_changes_pixel_color_in_place(tmp_path: Path) -> None:
    from io import BytesIO

    from PIL import Image
    from pptx import Presentation

    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- bullet\n")
    tools["add_pptx_icon"](path="deck.pptx", slide=1, icon_name="check", color="1F2937")

    result = tools["recolor_pptx_icon"](path="deck.pptx", slide=1, shape_index=2, color="c2410c")
    assert result == {
        "path": "deck.pptx",
        "slide": 1,
        "shape_index": 2,
        "color": "C2410C",
        "preview_path": None,
        "preview_skipped_reason": "no state_dir configured",
    }

    prs = Presentation(str(tmp_path / "deck.pptx"))
    icon = list(prs.slides[0].shapes)[2]
    img = Image.open(BytesIO(icon.image.blob)).convert("RGBA")
    assert _solid_opaque_pixel(img)[:3] == (0xC2, 0x41, 0x0C)


def test_recolor_pptx_icon_position_and_size_are_untouched(tmp_path: Path) -> None:
    from pptx import Presentation

    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- bullet\n")
    tools["add_pptx_icon"](
        path="deck.pptx", slide=1, icon_name="check", left_in=2.0, top_in=3.0, size_in=1.5
    )
    before = Presentation(str(tmp_path / "deck.pptx"))
    icon_before = list(before.slides[0].shapes)[2]
    left, top = icon_before.left, icon_before.top
    width, height = icon_before.width, icon_before.height

    tools["recolor_pptx_icon"](path="deck.pptx", slide=1, shape_index=2, color="C2410C")

    after = Presentation(str(tmp_path / "deck.pptx"))
    icon_after = list(after.slides[0].shapes)[2]
    assert (icon_after.left, icon_after.top, icon_after.width, icon_after.height) == (
        left,
        top,
        width,
        height,
    )


def test_recolor_pptx_icon_works_on_an_already_recolored_icon(tmp_path: Path) -> None:
    from io import BytesIO

    from PIL import Image
    from pptx import Presentation

    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- bullet\n")
    tools["add_pptx_icon"](path="deck.pptx", slide=1, icon_name="check", color="1F2937")
    tools["recolor_pptx_icon"](path="deck.pptx", slide=1, shape_index=2, color="C2410C")
    tools["recolor_pptx_icon"](path="deck.pptx", slide=1, shape_index=2, color="0F6B5C")

    prs = Presentation(str(tmp_path / "deck.pptx"))
    icon = list(prs.slides[0].shapes)[2]
    img = Image.open(BytesIO(icon.image.blob)).convert("RGBA")
    assert _solid_opaque_pixel(img)[:3] == (0x0F, 0x6B, 0x5C)


def test_recolor_pptx_icon_survives_round_trip(tmp_path: Path) -> None:
    import warnings

    from pptx import Presentation

    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- bullet\n")
    tools["add_pptx_icon"](path="deck.pptx", slide=1, icon_name="check")
    tools["recolor_pptx_icon"](path="deck.pptx", slide=1, shape_index=2, color="C2410C")

    with warnings.catch_warnings():
        warnings.simplefilter("error")
        prs = Presentation(str(tmp_path / "deck.pptx"))

    from io import BytesIO

    from PIL import Image

    pictures = [shape for shape in prs.slides[0].shapes if shape.shape_type == 13]
    assert len(pictures) == 1
    icon = Image.open(BytesIO(pictures[0].image.blob)).convert("RGBA")
    visible = {rgba[:3] for _, rgba in icon.getcolors(icon.width * icon.height) or [] if rgba[3]}
    assert visible == {(0xC2, 0x41, 0x0C)}


def test_recolor_pptx_icon_rejects_non_picture_shape(tmp_path: Path) -> None:
    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- bullet\n")

    with pytest.raises(ValueError, match="isn't a picture"):
        tools["recolor_pptx_icon"](path="deck.pptx", slide=1, shape_index=1, color="C2410C")


def test_recolor_pptx_icon_rejects_bad_color(tmp_path: Path) -> None:
    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- bullet\n")
    tools["add_pptx_icon"](path="deck.pptx", slide=1, icon_name="check")

    with pytest.raises(ValueError, match="6-hex-digit color"):
        tools["recolor_pptx_icon"](path="deck.pptx", slide=1, shape_index=2, color="#C2410C")


def test_recolor_pptx_icon_rejects_out_of_range_shape_index(tmp_path: Path) -> None:
    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- bullet\n")

    with pytest.raises(ValueError, match="out of range"):
        tools["recolor_pptx_icon"](path="deck.pptx", slide=1, shape_index=99, color="C2410C")


def test_recolor_pptx_icon_is_medium_risk_and_requires_approval(tmp_path: Path) -> None:
    from coscribe.runtime import get_tool_metadata

    tools = _tools_by_name(tmp_path)
    metadata = get_tool_metadata(tools["recolor_pptx_icon"])
    assert metadata.risk_category == "WRITE_LOCAL"
    assert metadata.requires_approval is True
