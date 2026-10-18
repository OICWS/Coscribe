"""The Slides panel's edits (design §3, decision 0016): a slide read as the parts the editor
places, and a slide written back as a section, after which the deck is built again.

An SVG page is read as the section it converts to and becomes that section only when the edit is
saved, so opening a slide to look at it changes nothing. A save is refused when the slide's file
changed since it was read (coscribe wrote it meanwhile), or when the .pptx was changed outside
coscribe, whose changes a build from the pages would throw away.
"""

from __future__ import annotations

import base64
import copy
import io
import os
import re
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

from PIL import Image
from pptx import Presentation

from ...._file_locks import file_lock, replace_with_retry
from .build import (
    MANIFEST,
    _read_manifest,
    _refuse_if_changed,
    _source_hash,
    build_deck,
    page_files,
)
from .compiler import SVG_NS
from .history import record_state
from .icons import expand_icons
from .section_format import SectionError, parse_section
from .section_view import Part, section_drawing
from .svg_to_section import convert_page
from .text_box import EMU_PER_PX
from .view import NotBuiltFromPages, _draw_natives, _inline_images, _make_safe, pages_folder

_ASSET_FORMATS = {"PNG": ".png", "JPEG": ".jpg", "GIF": ".gif", "WEBP": ".webp"}
MAX_ASSET_BYTES = 15 * 1024 * 1024
# Room around an element's own box in its picture: strokes, a chart's labels and an icon's
# lines are drawn a little past the box and would be cut off at it.
MARGIN = 24
_MAX_SOURCE = 400_000


class SlideChanged(Exception):
    """The slide's file is not the one the edit started from."""


def slide_parts(deck: Path, index: int, resource_root: Path) -> dict[str, Any]:
    """Slide `index` (from 0) for the editor: its section source, the version a save must name,
    and per element of the section its box (canvas px) and, for all but text, a picture of it
    alone (an SVG data URI covering the box plus `MARGIN`). Text is drawn by the editor itself."""
    folder, page = _page(deck, index)
    text = page.read_text(encoding="utf-8")
    source = text if page.suffix.lower() == ".html" else convert_page(text)[0]
    ET.register_namespace("", SVG_NS)
    found: list[Part] = []
    root = section_drawing(source, found)
    _make_safe(root)
    expand_icons(root)
    _inline_images(root, folder, resource_root.resolve())
    slides = Presentation(str(deck)).slides
    if index < len(slides):
        _draw_natives(root, slides[index], EMU_PER_PX)
    defs = [child for child in root if child.tag == f"{{{SVG_NS}}}defs"]
    section = parse_section(source)
    parts = []
    for (_elem, style), part in zip(section.elements, found, strict=True):
        try:
            box = list(style.box())
        except SectionError:
            box = None
        picture = None
        if part.kind == "drawing" and box is not None:
            picture = _picture(box, root.get("font-family", ""), defs, part.drawn)
        parts.append({"kind": part.kind, "box": box, "picture": picture})
    return {
        "name": page.name,
        "kind": "section" if page.suffix.lower() == ".html" else "page",
        "version": _source_hash(text),
        "source": source,
        "parts": parts,
    }


def save_slide(
    deck: Path, index: int, *, source: str, version: str, resource_root: Path
) -> dict[str, Any]:
    """Write `source` as slide `index`'s section and build the deck again. Raises SectionError
    for a section the language refuses, SlideChanged and DeckChangedError as the module says.
    Returns the slide's new file name and version, and the build's errors on it (text that no
    longer fits its box, ...): its advice to the model on style is not for the user."""
    if len(source) > _MAX_SOURCE:
        raise SectionError("the slide is too large")
    parse_section(source)
    with file_lock(deck):
        folder, page = _page(deck, index)
        if _source_hash(page.read_text(encoding="utf-8")) != version:
            raise SlideChanged(page.name)
        _refuse_if_changed(deck, _read_manifest(folder / MANIFEST))
        # The pages as they are before the change, so it can be undone even when no build was
        # recorded since they were written.
        record_state(folder, page_files(folder, (".svg", ".html")), "coscribe")
        target = page.with_suffix(".html")
        tmp = target.with_name(f".{target.name}.{os.getpid()}.tmp")
        tmp.write_text(source, encoding="utf-8")
        replace_with_retry(tmp, target)
        if page != target:
            page.unlink()
        report = build_deck(folder, deck, resource_root=resource_root, recorded_as="you")
    built = next((p for p in report.pages if p.name == target.name), None)
    return {
        "name": target.name,
        "version": _source_hash(target.read_text(encoding="utf-8")),
        "problems": built.errors if built else [],
    }


def add_slide_asset(deck: Path, name: str, data: bytes) -> dict[str, Any]:
    """Stores a picture the user inserts in the deck's `assets/` folder, under a free name, and
    returns its path as a section's `src` names it, with its size in px. Raises ValueError for
    anything that is not a PNG, JPEG, GIF or WebP picture, or one over 15 MB."""
    folder = pages_folder(deck)
    if folder is None:
        raise NotBuiltFromPages(f"{deck.name} was not built from pages")
    if len(data) > MAX_ASSET_BYTES:
        raise ValueError("the picture is larger than 15 MB")
    try:
        with Image.open(io.BytesIO(data)) as image:
            kind, (width, height) = image.format, image.size
    except (OSError, Image.DecompressionBombError) as e:
        raise ValueError("not a picture") from e
    if kind not in _ASSET_FORMATS:
        raise ValueError("pictures are PNG, JPEG, GIF or WebP")
    assets = folder / "assets"
    assets.mkdir(exist_ok=True)
    stem = re.sub(r"[^\w-]+", "-", Path(name).stem).strip("-")[:60] or "picture"
    target = assets / f"{stem}{_ASSET_FORMATS[kind]}"
    n = 1
    while target.exists():
        n += 1
        target = assets / f"{stem}-{n}{_ASSET_FORMATS[kind]}"
    target.write_bytes(data)
    return {"src": f"assets/{target.name}", "width": width, "height": height}


def _page(deck: Path, index: int) -> tuple[Path, Path]:
    folder = pages_folder(deck)
    if folder is None:
        raise NotBuiltFromPages(f"{deck.name} was not built from pages")
    entries = _read_manifest(folder / MANIFEST)["pages"]
    if not 0 <= index < len(entries):
        raise IndexError(f"no slide {index + 1}")
    return folder, folder / entries[index]["page"]


def _picture(box: list[float], font: str, defs: list[ET.Element], drawn: list[ET.Element]) -> str:
    x, y, width, height = box
    svg = ET.Element(
        f"{{{SVG_NS}}}svg",
        {
            "viewBox": f"{x - MARGIN:g} {y - MARGIN:g} {width + 2 * MARGIN:g} "
            f"{height + 2 * MARGIN:g}",
            "width": f"{width + 2 * MARGIN:g}",
            "height": f"{height + 2 * MARGIN:g}",
            "font-family": font,
        },
    )
    svg.extend(copy.deepcopy(d) for d in defs)
    svg.extend(copy.deepcopy(d) for d in drawn if d.tag != f"{{{SVG_NS}}}defs")
    data = ET.tostring(svg, encoding="unicode").encode("utf-8")
    return "data:image/svg+xml;base64," + base64.b64encode(data).decode()
