"""look_at_image: a picture file reaches the model as a picture it reads itself."""

from __future__ import annotations

import base64
import json
from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image

from coscribe.conversation import look_image
from coscribe.conversation.page_tools import build_page_tools
from coscribe.needs_permission import NeedsPermission
from coscribe.tools import WorkspaceScope, build_file_tools


def _tools(root: Path, state: Path | None = None) -> dict[str, object]:
    tools = [*build_file_tools(root), *build_page_tools(lambda: WorkspaceScope(root), state)]
    return {tool.__name__: tool for tool in tools}


def _picture(block: dict[str, object]) -> Image.Image:
    url = block["image_url"]["url"]  # type: ignore[index]
    assert url.startswith("data:image/png;base64,")
    return Image.open(BytesIO(base64.b64decode(url.split(",", 1)[1])))


def test_a_large_scan_is_shown_shrunk_with_its_real_size(tmp_path: Path):
    Image.new("RGB", (3000, 1500), "orange").save(tmp_path / "scan.jpg")

    note, picture = _tools(tmp_path)["look_at_image"]("scan.jpg")

    assert json.loads(note["text"]) == {
        "path": "scan.jpg",
        "size": "3000x1500",
        "shown": "1568x784",
    }
    assert _picture(picture).size == (1568, 784)


def test_a_phone_photo_is_shown_the_right_way_up(tmp_path: Path):
    photo = Image.new("RGB", (40, 20), "white")
    exif = photo.getexif()
    exif[0x0112] = 6  # stored sideways: turn 90 degrees clockwise to view
    photo.save(tmp_path / "photo.jpg", exif=exif)

    _, picture = _tools(tmp_path)["look_at_image"]("photo.jpg")

    assert _picture(picture).size == (20, 40)


def test_a_preview_a_render_tool_returned_opens_by_its_name(tmp_path: Path):
    state = tmp_path / "state"
    previews = state / "previews"
    previews.mkdir(parents=True)
    Image.new("RGBA", (64, 36), (255, 0, 0, 128)).save(previews / "deck-1.png")
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    note, picture = _tools(workspace, state)["look_at_image"]("deck-1.png")

    assert json.loads(note["text"])["path"] == "deck-1.png"
    assert _picture(picture).mode == "RGBA"


def test_a_palette_picture_keeps_its_transparency(tmp_path: Path):
    logo = Image.new("P", (8, 8), 0)
    logo.putpalette([255, 255, 255, 0, 0, 0])
    logo.putpixel((0, 0), 1)
    logo.save(tmp_path / "logo.png", transparency=0)

    _, picture = _tools(tmp_path)["look_at_image"]("logo.png")

    shown = _picture(picture)
    assert shown.mode == "RGBA"
    assert shown.getpixel((4, 4))[3] == 0
    assert shown.getpixel((0, 0))[3] == 255


def test_what_is_not_a_picture_is_refused(tmp_path: Path):
    (tmp_path / "notes.txt").write_text("hello", encoding="utf-8")
    (tmp_path / "fake.png").write_bytes(b"not a picture")
    look = _tools(tmp_path)["look_at_image"]

    with pytest.raises(ValueError, match="is not a picture"):
        look("notes.txt")
    with pytest.raises(ValueError, match="could not be opened as a picture"):
        look("fake.png")
    with pytest.raises(ValueError, match="does not exist"):
        look("missing.png")


def test_a_picture_outside_the_workspace_asks_the_person_first(tmp_path: Path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    Image.new("RGB", (4, 4)).save(tmp_path / "outside.png")

    with pytest.raises(NeedsPermission):
        _tools(workspace)["look_at_image"]("../outside.png")


def test_read_file_on_a_picture_points_to_look_at_image(tmp_path: Path):
    Image.new("RGB", (4, 4)).save(tmp_path / "chart.png")

    with pytest.raises(ValueError, match="look_at_image"):
        _tools(tmp_path)["read_file"]("chart.png")


def test_a_picture_too_large_in_pixels_is_refused(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(look_image, "_MAX_PIXELS", 100)
    Image.new("RGB", (20, 20)).save(tmp_path / "big.png")

    with pytest.raises(ValueError, match="too large"):
        look_image.image_blocks(tmp_path / "big.png", "big.png")


def test_a_region_is_cut_out_before_shrinking(tmp_path: Path):
    scan = Image.new("RGB", (4000, 2000), "white")
    scan.paste((255, 0, 0), (3000, 0, 4000, 1000))
    scan.save(tmp_path / "scan.png")

    note, picture = _tools(tmp_path)["look_at_image"]("scan.png", region="0.75,0,1,0.5")

    assert json.loads(note["text"])["region"] == "3000,0,4000,1000"
    shown = _picture(picture)
    assert shown.size == (1000, 1000)
    assert shown.convert("RGB").getpixel((500, 500)) == (255, 0, 0)


@pytest.mark.parametrize("region", ["0.5,0.5", "a,b,c,d", "0.6,0,0.4,1", "0,0,1.5,1"])
def test_a_region_that_is_not_a_box_inside_the_picture_is_refused(tmp_path: Path, region):
    Image.new("RGB", (10, 10)).save(tmp_path / "chart.png")

    with pytest.raises(ValueError, match="region"):
        _tools(tmp_path)["look_at_image"]("chart.png", region=region)


def test_a_turned_photo_reports_the_size_its_region_is_measured_against(tmp_path: Path):
    photo = Image.new("RGB", (400, 200), "white")
    exif = photo.getexif()
    exif[0x0112] = 6
    photo.save(tmp_path / "photo.jpg", exif=exif)

    note, _ = _tools(tmp_path)["look_at_image"]("photo.jpg", region="0,0,1,0.5")

    assert json.loads(note["text"]) | {"shown": None} == {
        "path": "photo.jpg",
        "size": "200x400",
        "shown": None,
        "region": "0,0,200,200",
    }
