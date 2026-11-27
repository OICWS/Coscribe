"""A picture in the workspace as the model sees it: a content block it reads with its own eyes.

Without it the agent knows a picture only through code it writes against the pixels, which
cannot read the words in a scan or tell a flowchart's boxes apart."""

from __future__ import annotations

import base64
import json
from io import BytesIO
from pathlib import Path
from typing import Any

IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".tif", ".tiff")
# What a vision model reads at full detail; a larger picture costs tokens and shows no more.
_MAX_SIDE = 1568
_MAX_BYTES = 50 * 1024 * 1024
# A picture this large in pixels is a decompression bomb or a scan no model reads whole.
_MAX_PIXELS = 100_000_000


def _box(region: str, width: int, height: int) -> tuple[int, int, int, int] | None:
    """The pixel box of "left,top,right,bottom" given as fractions of the picture, 0 to 1."""
    if not region.strip():
        return None
    try:
        left, top, right, bottom = (float(part) for part in region.split(","))
    except ValueError:
        raise ValueError('region is "left,top,right,bottom" as fractions 0-1') from None
    if not (0 <= left < right <= 1 and 0 <= top < bottom <= 1):
        raise ValueError("region needs 0 <= left < right <= 1 and 0 <= top < bottom <= 1")
    box = (round(left * width), round(top * height), round(right * width), round(bottom * height))
    return box[0], box[1], max(box[2], box[0] + 1), max(box[3], box[1] + 1)


def image_blocks(file: Path, shown_as: str, region: str = "") -> list[dict[str, Any]]:
    """A line on the picture and the picture itself (or the `region` of it, cut out before
    shrinking so small print stays legible), at most `_MAX_SIDE` pixels on its long side, as
    PNG. Raises ValueError for what is not a picture it can open."""
    from PIL import Image, ImageOps, UnidentifiedImageError

    if file.suffix.lower() not in IMAGE_SUFFIXES:
        raise ValueError(f"{shown_as} is not a picture ({', '.join(IMAGE_SUFFIXES)}).")
    if file.stat().st_size > _MAX_BYTES:
        raise ValueError(f"{shown_as} is over 50 MB; save a smaller copy and look at that.")
    try:
        with Image.open(file) as opened:
            if opened.size[0] * opened.size[1] > _MAX_PIXELS:
                raise ValueError(
                    f"{shown_as} is {opened.size[0]}x{opened.size[1]} pixels, too large to look at."
                )
            # A phone photo's pixels are stored sideways with a note to turn them.
            picture = ImageOps.exif_transpose(opened)
            # The size as seen, so a region's pixel box is measured against the same picture.
            width, height = picture.size
            # A palette PNG or GIF keeps its transparency in `info`, not in a band.
            clear = "A" in picture.getbands() or "transparency" in picture.info
            picture = picture.convert("RGBA" if clear else "RGB")
            box = _box(region, *picture.size)
            if box is not None:
                picture = picture.crop(box)
            picture.thumbnail((_MAX_SIDE, _MAX_SIDE))
            out = BytesIO()
            picture.save(out, format="PNG", optimize=True)
            shown = picture.size
    except (UnidentifiedImageError, Image.DecompressionBombError, OSError) as exc:
        raise ValueError(f"{shown_as} could not be opened as a picture: {exc}") from None
    note = {"path": shown_as, "size": f"{width}x{height}", "shown": f"{shown[0]}x{shown[1]}"}
    if box is not None:
        note["region"] = ",".join(str(edge) for edge in box)
    data = base64.b64encode(out.getvalue()).decode("ascii")
    return [
        {"type": "text", "text": json.dumps(note, ensure_ascii=False)},
        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{data}"}},
    ]
