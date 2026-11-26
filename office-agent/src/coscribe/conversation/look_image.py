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


def image_blocks(file: Path, shown_as: str) -> list[dict[str, Any]]:
    """A line on the picture and the picture itself, at most `_MAX_SIDE` pixels on its long
    side, as PNG. Raises ValueError for what is not a picture it can open."""
    from PIL import Image, ImageOps, UnidentifiedImageError

    if file.suffix.lower() not in IMAGE_SUFFIXES:
        raise ValueError(f"{shown_as} is not a picture ({', '.join(IMAGE_SUFFIXES)}).")
    if file.stat().st_size > _MAX_BYTES:
        raise ValueError(f"{shown_as} is over 50 MB; save a smaller copy and look at that.")
    try:
        with Image.open(file) as opened:
            width, height = opened.size
            if width * height > _MAX_PIXELS:
                raise ValueError(f"{shown_as} is {width}x{height} pixels, too large to look at.")
            # A phone photo's pixels are stored sideways with a note to turn them.
            picture = ImageOps.exif_transpose(opened)
            picture = picture.convert("RGBA" if "A" in picture.getbands() else "RGB")
            picture.thumbnail((_MAX_SIDE, _MAX_SIDE))
            out = BytesIO()
            picture.save(out, format="PNG", optimize=True)
            shown = picture.size
    except (UnidentifiedImageError, Image.DecompressionBombError, OSError) as exc:
        raise ValueError(f"{shown_as} could not be opened as a picture: {exc}") from None
    note = {"path": shown_as, "size": f"{width}x{height}", "shown": f"{shown[0]}x{shown[1]}"}
    data = base64.b64encode(out.getvalue()).decode("ascii")
    return [
        {"type": "text", "text": json.dumps(note, ensure_ascii=False)},
        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{data}"}},
    ]
