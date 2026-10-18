"""A built deck as the Slides panel shows it (decision 0016): its slides in order, each unedited
slide as one self-contained SVG the panel draws as an image.

The slides come from the pages folder whose last build wrote the deck. What PowerPoint would show
beyond the page (notes, transition, background, the native charts and tables) is read from the
built .pptx, so the panel shows what the user will get.
"""

from __future__ import annotations

import base64
import mimetypes
import re
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

from pptx import Presentation

from .build import MANIFEST, _read_manifest, _source_hash, slide_hashes
from .compiler import EMU_PER_PX, SVG_NS
from .icons import expand_icons
from .native import native_kind
from .view_native import native_drawings

_P = "{http://schemas.openxmlformats.org/presentationml/2006/main}"
_A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
_XLINK = "{http://www.w3.org/1999/xlink}href"
# Elements that could fetch or run something if the SVG were ever opened as a document; an
# image never runs them, but the route serves the SVG on the app's own origin.
_UNSAFE = {"script", "foreignObject", "iframe", "object", "embed"}
_SHAPES = {"sp", "pic", "graphicFrame", "grpSp", "cxnSp"}
# A comment's anchor names its element by the start of its words; past this it stops being a name.
_SNIPPET = 32
_IMAGE_TYPES = {"image/png", "image/jpeg", "image/gif", "image/webp", "image/svg+xml"}


class NotBuiltFromPages(ValueError):
    """The .pptx was not written by a build of a pages folder next to it."""


def pages_folder(deck: Path) -> Path | None:
    """The folder next to `deck` whose build wrote it, whether or not it changed since."""
    target = deck.resolve()
    for folder in deck.parent.iterdir():
        manifest = _read_manifest(folder / MANIFEST) if folder.is_dir() else {}
        if manifest and Path(manifest["deck"]).resolve() == target:
            return folder
    return None


def read_deck(deck: Path) -> dict[str, Any]:
    """The deck's slides for the panel. `changed` says the .pptx or a page differs from what the
    last build saw, so what the panel shows may not be what the file holds."""
    folder = pages_folder(deck)
    if folder is None:
        raise NotBuiltFromPages(f"{deck.name} was not built from pages")
    entries = _read_manifest(folder / MANIFEST)["pages"]
    prs = Presentation(str(deck))
    changed = [e["slide"] for e in entries] != slide_hashes(deck)
    slides = []
    for entry, slide in zip(entries, prs.slides, strict=False):
        page = folder / entry["page"]
        if not page.is_file() or _source_hash(page.read_text(encoding="utf-8")) != entry["source"]:
            changed = True
        slides.append(
            {
                "name": entry["page"],
                "kind": "page" if page.suffix.lower() == ".svg" else "section",
                "notes": _notes(slide),
                "transition": _transition(slide),
                "background": _background(slide),
                "elements": slide_elements(slide, prs.slide_width or 1, prs.slide_height or 1),
            }
        )
    return {"title": deck.stem, "folder": folder.name, "changed": changed, "slides": slides}


def slide_svg(deck: Path, index: int, resource_root: Path) -> str:
    """Slide `index` (from 0) as one SVG with nothing outside it: icons drawn, pictures inlined,
    native charts and tables drawn from the built deck. Raises IndexError for no such slide and
    NotBuiltFromPages; a slide that is a section raises ValueError (the panel draws those)."""
    folder = pages_folder(deck)
    if folder is None:
        raise NotBuiltFromPages(f"{deck.name} was not built from pages")
    entries = _read_manifest(folder / MANIFEST)["pages"]
    if not 0 <= index < len(entries):
        raise IndexError(f"no slide {index + 1}")
    page = folder / entries[index]["page"]
    if page.suffix.lower() != ".svg":
        raise ValueError(f"{page.name} is a section, not an SVG page")
    ET.register_namespace("", SVG_NS)
    ET.register_namespace("xlink", "http://www.w3.org/1999/xlink")
    root = ET.fromstring(page.read_text(encoding="utf-8"))
    _make_safe(root)
    expand_icons(root)
    _inline_images(root, page.parent, resource_root.resolve())
    slides = Presentation(str(deck)).slides
    if index < len(slides):
        _draw_natives(root, slides[index])
    return ET.tostring(root, encoding="unicode")


def slide_elements(slide: Any, width: int, height: int) -> list[dict[str, Any]]:
    """What a comment can be put on: every shape, inside groups too, with its box as fractions of
    the slide and a label that names it ("Title", 'Text "Q3 at a glance"', "Chart")."""
    found: list[dict[str, Any]] = []
    _collect(slide.shapes._spTree, (0.0, 0.0, 1.0, 1.0), width, height, found)
    return found


def _collect(
    tree: Any, place: tuple[float, float, float, float], width: int, height: int, found: list[Any]
) -> None:
    """`place` maps the tree's child coordinates to the slide: (offset x, offset y, scale x,
    scale y), in EMU, as a group's chOff/chExt to off/ext says."""
    ox, oy, sx, sy = place
    for el in tree:
        tag = el.tag.rsplit("}", 1)[-1] if isinstance(el.tag, str) else ""
        if tag not in _SHAPES:
            continue
        xfrm = el.find(f"{_P}grpSpPr/{_A}xfrm") if tag == "grpSp" else _xfrm(el)
        if xfrm is None:
            continue
        x, y, w, h = _rect(xfrm)
        box = (ox + x * sx, oy + y * sy, w * sx, h * sy)
        if tag == "grpSp":
            ch_off, ch_ext = xfrm.find(f"{_A}chOff"), xfrm.find(f"{_A}chExt")
            if ch_off is None or ch_ext is None:
                continue
            cx, cy = int(ch_off.get("x", 0)), int(ch_off.get("y", 0))
            cw, ch = int(ch_ext.get("cx", 1)) or 1, int(ch_ext.get("cy", 1)) or 1
            gx, gy = box[2] / cw, box[3] / ch
            _collect(el, (box[0] - cx * gx, box[1] - cy * gy, gx, gy), width, height, found)
            continue
        cnv = el.find(f".//{_P}cNvPr")
        found.append(
            {
                "id": cnv.get("id") if cnv is not None else "",
                "label": _label(el, tag),
                "box": [box[0] / width, box[1] / height, box[2] / width, box[3] / height],
            }
        )


def _xfrm(el: Any) -> Any:
    found = el.find(f"{_P}spPr/{_A}xfrm")
    if found is None:
        found = el.find(f"{_P}xfrm")
    return found


def _rect(xfrm: Any) -> tuple[float, float, float, float]:
    off, ext = xfrm.find(f"{_A}off"), xfrm.find(f"{_A}ext")
    if off is None or ext is None:
        return 0.0, 0.0, 0.0, 0.0
    return (
        float(off.get("x", 0)),
        float(off.get("y", 0)),
        float(ext.get("cx", 0)),
        float(ext.get("cy", 0)),
    )


def _label(el: Any, tag: str) -> str:
    if tag == "pic":
        return "Picture"
    if tag == "cxnSp":
        return "Line"
    if tag == "graphicFrame":
        uri = el.find(f".//{_A}graphicData")
        kind = (uri.get("uri", "") if uri is not None else "").rsplit("/", 1)[-1]
        return {"chart": "Chart", "table": "Table"}.get(kind, "Object")
    words = " ".join("".join(t.text or "" for t in p.iter(f"{_A}t")) for p in el.iter(f"{_A}p"))
    words = " ".join(words.split())
    if el.find(f".//{_P}ph[@type='title']") is not None:
        return f'Title "{_snippet(words)}"' if words else "Title"
    return f'Text "{_snippet(words)}"' if words else "Shape"


def _snippet(words: str) -> str:
    return words if len(words) <= _SNIPPET else words[: _SNIPPET - 1] + "…"


def _make_safe(root: ET.Element) -> None:
    for parent in list(root.iter()):
        for child in list(parent):
            if not isinstance(child.tag, str):
                continue
            if child.tag.rsplit("}", 1)[-1] in _UNSAFE:
                parent.remove(child)
                continue
            for name in [n for n in child.attrib if n.lower().startswith("on")]:
                del child.attrib[name]
    for name in [n for n in root.attrib if n.lower().startswith("on")]:
        del root.attrib[name]


def _inline_images(root: ET.Element, folder: Path, resource_root: Path) -> None:
    """A picture becomes a data URI: an SVG drawn as an image loads nothing from outside it."""
    for image in root.iter(f"{{{SVG_NS}}}image"):
        key = "href" if "href" in image.attrib else _XLINK
        href = image.get(key, "")
        if href.startswith("data:"):
            continue
        data = _image_uri(href, folder, resource_root)
        image.attrib.pop("href", None)
        image.attrib.pop(_XLINK, None)
        if data:
            image.set("href", data)


def _image_uri(href: str, folder: Path, resource_root: Path) -> str | None:
    if not href or re.match(r"^[a-z][a-z0-9+.-]*:", href, re.I):
        return None
    path = (folder / href).resolve()
    kind = mimetypes.guess_type(path.name)[0]
    if kind not in _IMAGE_TYPES or not path.is_file() or not path.is_relative_to(resource_root):
        return None
    return f"data:{kind};base64,{base64.b64encode(path.read_bytes()).decode()}"


def _draw_natives(root: ET.Element, slide: Any) -> None:
    font = root.get("font-family", "Microsoft YaHei, Arial")
    groups = [g for g in root.iter(f"{{{SVG_NS}}}g") if native_kind(g)]
    drawings = native_drawings(slide, EMU_PER_PX, font)
    for group, markup in zip(groups, drawings, strict=False):
        for child in list(group):
            group.remove(child)
        for attr in [a for a in group.attrib if a != "id"]:
            del group.attrib[attr]
        if markup:
            group.append(ET.fromstring(f'<g xmlns="{SVG_NS}">{markup}</g>'))


def _notes(slide: Any) -> str:
    if not slide.has_notes_slide:
        return ""
    return str(slide.notes_slide.notes_text_frame.text or "")


def _transition(slide: Any) -> str | None:
    """PowerPoint's name for the slide's transition, None without one. Morph sits in an
    mc:AlternateContent, so it is found anywhere in the slide's top level."""
    for element in slide._element.iter(f"{_P}transition", "{*}transition"):
        kinds = [c.tag.rsplit("}", 1)[-1] for c in element if isinstance(c.tag, str)]
        kinds = [k for k in kinds if k not in {"sndAc", "extLst"}]
        if kinds:
            return kinds[0]
    return None


def _background(slide: Any) -> str | None:
    fill = slide._element.find(f"{_P}cSld/{_P}bg/{_P}bgPr/{_A}solidFill/{_A}srgbClr")
    return f"#{fill.get('val')}" if fill is not None else None
