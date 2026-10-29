"""A deck built from pages on the user's own template: the pages' slides are made from the
template's layouts, so its slide master (background, logo, theme colours and fonts) carries
over, and the pages draw the content. The template's own example slides are left out, but a
page can start from one (`data-template-slide="2"`): many templates draw their design on the
example slides, not on the master, and copying that decoration keeps it exact.

`describe` is what the model needs to design pages that belong to the template: the canvas,
the theme's colours and fonts, and the decoration its example slides draw on top of the master.
"""

from __future__ import annotations

import copy
import io
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from lxml import etree
from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE
from pptx.opc.constants import RELATIONSHIP_TYPE as RT

EMU_PER_PX = 9525
_A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
_P = "{http://schemas.openxmlformats.org/presentationml/2006/main}"
_R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
_SLOTS = (
    "dk1",
    "lt1",
    "dk2",
    "lt2",
    "accent1",
    "accent2",
    "accent3",
    "accent4",
    "accent5",
    "accent6",
)
_DEFAULT_LAYOUT = "Title Only"
_TEMPLATE_TYPE = b"presentationml.template.main+xml"
_PRESENTATION_TYPE = b"presentationml.presentation.main+xml"


@dataclass
class Example:
    """What one example slide draws besides its placeholders, to put under a page. `parts` holds
    each relationship the copied XML refers to: an image's bytes, or an external target (a
    hyperlink). `dropped` names the shapes left out because they refer to anything else (a chart,
    SmartArt, media, a link to another slide), which a copy cannot carry."""

    layout: Any
    background: Any
    shapes: list[Any]
    parts: dict[str, bytes | tuple[str, str]]
    dropped: list[str]


def open_template(path: Path) -> tuple[Any, list[Example]]:
    """The template with its example slides removed, and what each of them drew."""
    prs = _load(path)
    examples = [_example(slide) for slide in prs.slides]
    slide_ids = prs.element.sldIdLst
    for slide_id in list(slide_ids):
        prs.part.drop_rel(slide_id.rId)
        slide_ids.remove(slide_id)
    return prs, examples


def _load(path: Path) -> Any:
    """The file as a presentation; a .potx is read as the .pptx it would make, which python-pptx
    otherwise refuses for its content type."""
    data = path.read_bytes()
    with zipfile.ZipFile(io.BytesIO(data)) as package:
        types = package.read("[Content_Types].xml")
        if _TEMPLATE_TYPE not in types:
            return Presentation(io.BytesIO(data))
        converted = io.BytesIO()
        with zipfile.ZipFile(converted, "w", zipfile.ZIP_DEFLATED) as out:
            for item in package.infolist():
                content = package.read(item)
                if item.filename == "[Content_Types].xml":
                    content = content.replace(_TEMPLATE_TYPE, _PRESENTATION_TYPE)
                out.writestr(item, content)
    return Presentation(converted)


def start_from(slide: Any, example: Example) -> list[Any]:
    """Put the example's background and decoration under what the page will draw; the copied
    shapes are returned so `renumber` can give them ids of their own once the page is drawn."""
    if example.background is not None:
        background = copy.deepcopy(example.background)
        _relink(slide, background, example.parts)
        slide.element.cSld.insert(0, background)
    tree = slide.element.cSld.spTree
    anchor = tree.find(f"{_P}grpSpPr")
    copied = []
    for shape in reversed(example.shapes):
        element = copy.deepcopy(shape)
        _relink(slide, element, example.parts)
        anchor.addnext(element)
        copied.append(element)
    return copied


def renumber(slide: Any, copied: list[Any]) -> None:
    """Give the copied shapes ids above every other shape's: the example's ids are low numbers
    the page's own shapes also use, and the edit tools find a shape by its id. A connector
    between two copied shapes follows them."""
    ours = [node for element in copied for node in element.iter(f"{_P}cNvPr")]
    taken = [
        int(node.get("id"))
        for node in slide.element.cSld.spTree.iter(f"{_P}cNvPr")
        if not any(node is mine for mine in ours) and str(node.get("id", "")).isdigit()
    ]
    next_id = max(taken, default=1) + 1
    moved: dict[str, str] = {}
    for node in ours:
        moved[node.get("id")] = str(next_id)
        node.set("id", str(next_id))
        next_id += 1
    for element in copied:
        for node in element.iter(f"{_A}stCxn", f"{_A}endCxn"):
            if node.get("id") in moved:
                node.set("id", moved[node.get("id")])


def _relink(slide: Any, element: Any, parts: dict[str, bytes | tuple[str, str]]) -> None:
    for node in element.iter():
        for attribute, old in node.attrib.items():
            if not attribute.startswith(_R) or old not in parts:
                continue
            part = parts[old]
            if isinstance(part, bytes):
                _image, new = slide.part.get_or_add_image_part(io.BytesIO(part))
            else:
                reltype, target = part
                new = slide.part.relate_to(target, reltype, is_external=True)
            node.set(attribute, new)


def _example(slide: Any) -> Example:
    rels = slide.part.rels
    parts: dict[str, bytes | tuple[str, str]] = {}

    def copyable(element: Any) -> bool:
        for node in element.iter():
            for attribute, rel_id in node.attrib.items():
                if not attribute.startswith(_R):
                    continue
                rel = rels.get(rel_id)
                if rel is None:
                    return False
                if rel.is_external and rel.reltype == RT.HYPERLINK:
                    parts[rel_id] = (rel.reltype, rel.target_ref)
                elif not rel.is_external and rel.reltype == RT.IMAGE:
                    parts[rel_id] = rel.target_part.blob
                else:
                    return False
        return True

    background = slide.element.cSld.bg
    shapes, dropped = [], []
    if background is not None and not copyable(background):
        background, dropped = None, ["the background"]
    for shape in slide.shapes:
        if shape.is_placeholder:
            continue
        if copyable(shape.element):
            shapes.append(shape.element)
        else:
            dropped.append(f'"{shape.name}"')
    return Example(slide.slide_layout, background, shapes, parts, dropped)


def canvas(prs: Any) -> tuple[int, int]:
    """The pages' viewBox size in px for this deck's slide size."""
    return round(prs.slide_width / EMU_PER_PX), round(prs.slide_height / EMU_PER_PX)


def layout(prs: Any, name: str | None) -> Any:
    """The layout a page asks for by name (`data-layout` on its root), else a title-only one."""
    layouts = list(prs.slide_layouts)
    wanted = (name or _DEFAULT_LAYOUT).strip().lower()
    for candidate in layouts:
        if candidate.name.strip().lower() == wanted:
            return candidate
    if name:
        names = ", ".join(f'"{candidate.name}"' for candidate in layouts)
        raise ValueError(f'no layout named "{name}" in the template; it has {names}')
    return min(layouts, key=lambda candidate: len(candidate.placeholders))


def describe(path: Path) -> dict[str, object]:
    """The canvas, theme and decoration of a template, in page terms (px, #RRGGBB)."""
    prs = _load(path)
    width, height = canvas(prs)
    theme = etree.fromstring(prs.slide_masters[0].part.part_related_by(RT.THEME).blob)
    colours = {}
    for slot in _SLOTS:
        node = theme.find(f".//{_A}clrScheme/{_A}{slot}")
        value = None if node is None else _colour(node)
        if value:
            colours[slot] = value
    fonts = {}
    for role in ("majorFont", "minorFont"):
        for script in ("latin", "ea"):
            node = theme.find(f".//{_A}fontScheme/{_A}{role}/{_A}{script}")
            if node is not None and node.get("typeface"):
                fonts[f"{role[:5]}_{script}"] = node.get("typeface")
    background = _paint(prs.slide_masters[0].element.find(f".//{_P}bg/{_P}bgPr"))
    return {
        "viewBox": f"0 0 {width} {height}",
        "background": background,
        "colours": colours,
        "fonts": fonts,
        "layouts": [candidate.name for candidate in prs.slide_layouts],
        "example_slides": [
            {
                "slide": number,
                "layout": slide.slide_layout.name,
                "background": _paint(slide.element.find(f".//{_P}bg/{_P}bgPr")) or background,
                "decoration": [_shape(shape) for shape in slide.shapes if not shape.is_placeholder],
                "text": [
                    shape.text_frame.text.strip()[:60]
                    for shape in slide.shapes
                    if shape.is_placeholder
                    and shape.has_text_frame
                    and shape.text_frame.text.strip()
                ],
            }
            for number, slide in enumerate(prs.slides, start=1)
        ],
    }


def _shape(shape: Any) -> dict[str, object]:
    box = [
        round((value or 0) / EMU_PER_PX)
        for value in (shape.left, shape.top, shape.width, shape.height)
    ]
    info: dict[str, object] = {
        "kind": _kind(shape),
        "x": box[0],
        "y": box[1],
        "width": box[2],
        "height": box[3],
    }
    paint = _paint(shape.element.find(f".//{_P}spPr"))
    if paint:
        info["fill"] = paint
    # A page starting from this slide gets these words too and cannot take them off, so the
    # model must see them to pick another slide or the bare layout.
    if shape.has_text_frame and shape.text_frame.text.strip():
        info["text"] = shape.text_frame.text.strip()[:60]
    return info


def _paint(properties: Any) -> str | list[str] | None:
    """A solid fill's colour, or a gradient's stop colours in order."""
    if properties is None:
        return None
    solid = properties.find(f"{_A}solidFill")
    if solid is not None:
        return _colour(solid)
    gradient = properties.find(f"{_A}gradFill")
    if gradient is not None:
        stops = [_colour(stop) for stop in gradient.iter(f"{_A}gs")]
        return [stop for stop in stops if stop] or None
    return None


def _kind(shape: Any) -> str:
    if getattr(shape, "has_table", False) and shape.has_table:
        return "table"
    if shape.shape_type == MSO_SHAPE_TYPE.PICTURE:
        return "picture"
    if shape.shape_type == MSO_SHAPE_TYPE.GROUP:
        return "group"
    return "shape"


def _colour(node: Any) -> str | None:
    rgb = node.find(f"{_A}srgbClr")
    if rgb is not None:
        return f"#{rgb.get('val', '').upper()}"
    system = node.find(f"{_A}sysClr")
    if system is not None and system.get("lastClr"):
        return f"#{system.get('lastClr', '').upper()}"
    scheme = node.find(f"{_A}schemeClr")
    return None if scheme is None else f"theme:{scheme.get('val')}"
