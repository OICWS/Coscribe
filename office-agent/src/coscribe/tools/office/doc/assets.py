"""Pictures of a Doc: kept in `assets/` of its side folder, so they travel with it, and named in the
markdown by the path from the Doc's own folder (`plan.doc/assets/chart.png`)."""

from __future__ import annotations

import io
import re
from pathlib import Path
from typing import Any

from PIL import Image

from .files import side_folder

MAX_ASSET_BYTES = 8 * 1024 * 1024
_FORMATS = {"PNG": ".png", "JPEG": ".jpg", "GIF": ".gif", "WEBP": ".webp"}
_MEDIA = {".png": "image/png", ".jpg": "image/jpeg", ".gif": "image/gif", ".webp": "image/webp"}
_FILE_NAME = re.compile(r"[\w-][\w.-]*")


class DocAssetRefused(ValueError):
    """A picture this module will not keep. `code` says why (`too_big`, `not_a_picture` or
    `format`); the caller shows its own text for it, never this exception's."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def add_doc_asset(path: Path, name: str, data: bytes) -> dict[str, Any]:
    """Keeps a picture the person adds under a free name and returns `src`, the path the markdown
    names it by, and its size in px. `DocAssetRefused` for anything that is not a PNG, JPEG, GIF or
    WebP picture, or is over 8 MB."""
    if len(data) > MAX_ASSET_BYTES:
        raise DocAssetRefused("too_big")
    try:
        with Image.open(io.BytesIO(data)) as image:
            kind, (width, height) = image.format, image.size
    except (OSError, Image.DecompressionBombError) as error:
        raise DocAssetRefused("not_a_picture") from error
    if kind not in _FORMATS:
        raise DocAssetRefused("format")
    folder = side_folder(path)
    assets = folder / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    stem = re.sub(r"[^\w-]+", "-", Path(name).stem).strip("-")[:60] or "picture"
    ext = _FORMATS[kind]
    target = assets / f"{stem}{ext}"
    n = 1
    while target.exists():
        n += 1
        target = assets / f"{stem}-{n}{ext}"
    target.write_bytes(data)
    return {"src": f"{folder.name}/assets/{target.name}", "width": width, "height": height}


def read_doc_asset(path: Path, src: str) -> tuple[bytes, str] | None:
    """The bytes and media type of a picture of this Doc named by its markdown path, or None for
    a path that is not one of its pictures (another folder, a parent, a file that is not one)."""
    folder = side_folder(path)
    prefix, _, name = src.rpartition("/")
    if prefix != f"{folder.name}/assets" or not _FILE_NAME.fullmatch(name):
        return None
    media = _MEDIA.get(Path(name).suffix.lower())
    file = folder / "assets" / name
    if media is None or not file.is_file():
        return None
    return file.read_bytes(), media
