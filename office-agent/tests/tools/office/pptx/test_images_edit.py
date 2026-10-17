from pathlib import Path

import pytest

from .helpers import (
    _make_test_png,
    _tools_by_name,
)

# --- crop_pptx_image (Tier 2: general picture cropping) ---


def test_crop_pptx_image_sets_crop_fractions(tmp_path: Path) -> None:
    from pptx import Presentation

    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- bullet")
    _make_test_png(tmp_path / "red.png")
    tools["add_pptx_image"](
        path="deck.pptx", slide=1, image_path="red.png", left=1.0, top=1.0, width=2.0, height=2.0
    )
    shapes = tools["list_pptx_shapes"](path="deck.pptx", slide=1)["shapes"]
    pic_index = next(s["index"] for s in shapes if s["is_picture"])

    result = tools["crop_pptx_image"](
        path="deck.pptx",
        slide=1,
        shape_index=pic_index,
        crop_left=0.1,
        crop_right=0.2,
        crop_top=0.05,
        crop_bottom=0.15,
    )
    assert result["crop_left"] == 0.1

    prs = Presentation(tmp_path / "deck.pptx")
    shape = list(prs.slides[0].shapes)[pic_index]
    assert shape.crop_left == pytest.approx(0.1)
    assert shape.crop_right == pytest.approx(0.2)
    assert shape.crop_top == pytest.approx(0.05)
    assert shape.crop_bottom == pytest.approx(0.15)


def test_crop_pptx_image_leaves_position_and_size_untouched(tmp_path: Path) -> None:

    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- bullet")
    _make_test_png(tmp_path / "red.png")
    tools["add_pptx_image"](
        path="deck.pptx", slide=1, image_path="red.png", left=1.0, top=1.0, width=2.0, height=2.0
    )
    shapes = tools["list_pptx_shapes"](path="deck.pptx", slide=1)["shapes"]
    pic_index = next(s["index"] for s in shapes if s["is_picture"])
    before = shapes[pic_index]

    tools["crop_pptx_image"](path="deck.pptx", slide=1, shape_index=pic_index, crop_left=0.3)

    after = tools["list_pptx_shapes"](path="deck.pptx", slide=1)["shapes"][pic_index]
    assert after["left_in"] == before["left_in"]
    assert after["top_in"] == before["top_in"]
    assert after["width_in"] == before["width_in"]
    assert after["height_in"] == before["height_in"]


def test_crop_pptx_image_rejects_out_of_range_fraction(tmp_path: Path) -> None:
    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- bullet")
    _make_test_png(tmp_path / "red.png")
    tools["add_pptx_image"](path="deck.pptx", slide=1, image_path="red.png")
    shapes = tools["list_pptx_shapes"](path="deck.pptx", slide=1)["shapes"]
    pic_index = next(s["index"] for s in shapes if s["is_picture"])

    with pytest.raises(ValueError, match=r"\[0\.0, 1\.0\)"):
        tools["crop_pptx_image"](path="deck.pptx", slide=1, shape_index=pic_index, crop_left=1.0)


def test_crop_pptx_image_rejects_left_plus_right_over_one(tmp_path: Path) -> None:
    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- bullet")
    _make_test_png(tmp_path / "red.png")
    tools["add_pptx_image"](path="deck.pptx", slide=1, image_path="red.png")
    shapes = tools["list_pptx_shapes"](path="deck.pptx", slide=1)["shapes"]
    pic_index = next(s["index"] for s in shapes if s["is_picture"])

    with pytest.raises(ValueError, match="crop_left"):
        tools["crop_pptx_image"](
            path="deck.pptx", slide=1, shape_index=pic_index, crop_left=0.6, crop_right=0.6
        )


def test_crop_pptx_image_rejects_non_picture_shape(tmp_path: Path) -> None:
    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- bullet")
    with pytest.raises(ValueError, match="isn't a picture"):
        tools["crop_pptx_image"](path="deck.pptx", slide=1, shape_index=0, crop_left=0.1)


# --- replace_pptx_image (Tier 1 #3: image replacement, preserves placement) ---


def test_replace_pptx_image_keeps_position_size_swaps_pixels(tmp_path: Path) -> None:
    from pptx import Presentation

    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- bullet\n")
    _make_test_png(tmp_path / "red.png")
    tools["add_pptx_image"](
        path="deck.pptx", slide=1, image_path="red.png", left=1.0, top=1.0, width=2.0, height=2.0
    )

    from PIL import Image

    Image.new("RGB", (50, 50), color="blue").save(tmp_path / "blue.png")

    shapes = tools["list_pptx_shapes"](path="deck.pptx", slide=1)["shapes"]
    pic_index = next(s["index"] for s in shapes if s["is_picture"])

    result = tools["replace_pptx_image"](
        path="deck.pptx", slide=1, shape_index=pic_index, image_path="blue.png"
    )
    assert result["shape_index"] == pic_index

    prs = Presentation(str(tmp_path / "deck.pptx"))
    shape = list(prs.slides[0].shapes)[pic_index]
    from pptx.util import Inches

    assert shape.left == Inches(1.0)
    assert shape.top == Inches(1.0)
    assert shape.width == Inches(2.0)
    assert shape.height == Inches(2.0)
    assert shape.image.size == (50, 50)


def test_replace_pptx_image_rejects_out_of_range_shape_index(tmp_path: Path) -> None:
    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- bullet\n")
    _make_test_png(tmp_path / "red.png")
    with pytest.raises(ValueError, match="out of range"):
        tools["replace_pptx_image"](path="deck.pptx", slide=1, shape_index=99, image_path="red.png")


def test_replace_pptx_image_rejects_non_picture_shape(tmp_path: Path) -> None:
    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- bullet\n")
    _make_test_png(tmp_path / "red.png")
    with pytest.raises(ValueError, match="isn't a picture"):
        tools["replace_pptx_image"](path="deck.pptx", slide=1, shape_index=0, image_path="red.png")


def test_replace_pptx_image_on_missing_file_raises(tmp_path: Path) -> None:
    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- bullet\n")
    _make_test_png(tmp_path / "red.png")
    tools["add_pptx_image"](path="deck.pptx", slide=1, image_path="red.png")
    shapes = tools["list_pptx_shapes"](path="deck.pptx", slide=1)["shapes"]
    pic_index = next(s["index"] for s in shapes if s["is_picture"])

    with pytest.raises(ValueError, match="does not exist"):
        tools["replace_pptx_image"](
            path="deck.pptx", slide=1, shape_index=pic_index, image_path="missing.png"
        )
