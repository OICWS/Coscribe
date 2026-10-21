"""The pictures of a document for the Docs editor: those a paragraph shows, and one's bytes."""

from __future__ import annotations

from pathlib import Path
from typing import Any

_R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_A = "http://schemas.openxmlformats.org/drawingml/2006/main"
_MAX_SHOWN = 4
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
