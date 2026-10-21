"""The pictures of a document for the Docs editor: those a paragraph shows, one's bytes, and a
picture the person adds."""

from __future__ import annotations

import base64
import binascii
import io
from pathlib import Path
from typing import Any

_R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_A = "http://schemas.openxmlformats.org/drawingml/2006/main"
_MAX_SHOWN = 4
_MAX_BYTES = 8 * 1024 * 1024
_MAX_WIDTH = 914400 * 6  # six inches in EMU: what fits a page with ordinary margins
# Formats a browser draws from an <img>; vector and legacy formats (svg, emf, wmf) stay a grey line.
_DRAWABLE = {"image/png", "image/jpeg", "image/gif", "image/webp"}


def images_of(element: Any) -> list[str]:
    """Relationship ids of the pictures a paragraph embeds, in order."""
    ids = (blip.get(f"{{{_R}}}embed") for blip in element.iter(f"{{{_A}}}blip"))
    return [rid for rid in ids if rid][:_MAX_SHOWN]


def read_doc_image(path: Path, rid: str) -> tuple[bytes, str] | None:
    """The bytes and media type of a picture the document embeds, None for anything else."""
    from docx import Document

    part = Document(str(path)).part.related_parts.get(rid)
    if part is None or part.content_type not in _DRAWABLE:
        return None
    return part.blob, part.content_type


def decode_picture(data: Any) -> bytes:
    """The bytes of a picture the editor sends (base64 or a data url); ValueError, with a text that
    is safe to show, when it is not a picture a document can hold."""
    from docx.image.image import Image

    if not isinstance(data, str):
        raise ValueError("A picture could not be read")
    try:
        blob = base64.b64decode(data.partition(",")[2] if data.startswith("data:") else data)
    except (binascii.Error, ValueError):
        raise ValueError("A picture could not be read") from None
    if len(blob) > _MAX_BYTES:
        raise ValueError("A picture can be at most 8 MB")
    try:
        found = Image.from_blob(blob)
    except Exception:  # the parser raises a different error for each way a file can be broken
        raise ValueError("Only PNG, JPEG, GIF and WebP pictures can be added") from None
    if found.content_type not in _DRAWABLE:
        raise ValueError("Only PNG, JPEG, GIF and WebP pictures can be added")
    return blob


def new_picture_paragraph(document: Any, blob: bytes) -> Any:
    """A paragraph holding the picture, at its own size but no wider than a page."""
    from docx.oxml import OxmlElement

    stream = io.BytesIO(blob)
    inline = document.part.new_pic_inline(
        stream, _MAX_WIDTH if _native_width(stream) > _MAX_WIDTH else None, None
    )
    drawing = OxmlElement("w:drawing")
    drawing.append(inline)
    run = OxmlElement("w:r")
    run.append(drawing)
    paragraph = OxmlElement("w:p")
    paragraph.append(run)
    return paragraph


def _native_width(stream: io.BytesIO) -> int:
    """The picture's own width in EMU; leaves the stream at its start."""
    from docx.image.image import Image

    width = int(Image.from_file(stream).width)
    stream.seek(0)
    return width
