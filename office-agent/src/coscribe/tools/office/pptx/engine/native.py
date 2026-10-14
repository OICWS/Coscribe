"""Native charts and tables on a page: a group marked `data-pptx-replace-with="chart"` (or
`"table"`) holding its data as JSON is compiled by the copied converter into a PowerPoint chart
(with its data as an embedded workbook, editable in PowerPoint) or table, instead of shapes.

The converter writes a chart's parts (chart XML, its relationships, the workbook) as a flat
`{part name: content}` map numbered per slide; python-pptx owns the package, so each part is
added as a python-pptx part under a name the package has free, with its relationships rebuilt.
"""

from __future__ import annotations

import posixpath
import re
from typing import Any
from xml.etree import ElementTree as ET

from pptx.opc.package import Part
from pptx.opc.packuri import PackURI

from ...._native_svg.svg_to_pptx.drawingml.context import ShapeResult
from ...._native_svg.svg_to_pptx.native_objects import convert_native_object
from ...._native_svg.svg_to_pptx.native_objects.marker_attributes import (
    NATIVE_AUTHORITY_ATTR as AUTHORITY_ATTR,
)
from ...._native_svg.svg_to_pptx.native_objects.marker_attributes import native_replacement_kind

_RELS_NS = "{http://schemas.openxmlformats.org/package/2006/relationships}"
_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
KINDS = ("chart", "table")


def native_kind(elem: ET.Element) -> str | None:
    """`chart` or `table` when the element asks to be one, else None."""
    try:
        kind = native_replacement_kind(elem)
    except Exception:  # an unusable marker is reported by the conversion itself
        return elem.get("data-pptx-replace-with")
    return kind if kind in KINDS else None


def convert(elem: ET.Element, ctx: Any) -> ShapeResult | None:
    """The chart or table as a graphic frame. A page writes the data only, never a drawn copy
    of the chart beside it, so the JSON is the authority."""
    ctx.native_objects_enabled = True
    elem.set(AUTHORITY_ATTR, "json")
    return convert_native_object(elem, ctx)


def add_part(slide: Any, ctx: Any, target: str) -> Any:
    """The part a slide relationship's `target` names, added to the deck with its own parts."""
    name = posixpath.normpath(posixpath.join("ppt/slides", target))
    return _part(slide.part.package, ctx, name, {})


def _part(package: Any, ctx: Any, name: str, made: dict[str, Any]) -> Any:
    """The part `name` with the parts it refers to. Its children are made first, so its own
    relationships get the ids `rId1`, `rId2`... in order and its XML is rewritten to them before
    the part exists."""
    if name in made:
        return made[name]
    rels_name = posixpath.join(posixpath.dirname(name), "_rels", posixpath.basename(name) + ".rels")
    children = []
    for rel in ET.fromstring(ctx.package_files.get(rels_name) or "<r/>").iter(
        f"{_RELS_NS}Relationship"
    ):
        target = posixpath.normpath(posixpath.join(posixpath.dirname(name), rel.get("Target", "")))
        children.append((rel.get("Id", ""), rel.get("Type", ""), _part(package, ctx, target, made)))
    content = ctx.package_files[name]
    blob = content.encode("utf-8") if isinstance(content, str) else content
    ids = {old: f"rId{index}" for index, (old, _, _) in enumerate(children, start=1)}
    part = Part(
        PackURI(package.next_partname(re.sub(r"\d+(?=\.\w+$)", "%d", f"/{name}"))),
        ctx.content_type_overrides.get(name) or _content_type(name),
        package,
        _rename_ids(blob, ids),
    )
    for old, kind, child in children:
        if part.relate_to(child, kind) != ids[old]:
            raise RuntimeError(f"relationship ids of {name} came out of order")
    made[name] = part
    return part


def _rename_ids(blob: bytes, mapping: dict[str, str]) -> bytes:
    if all(old == new for old, new in mapping.items()):
        return blob
    text = blob.decode("utf-8")
    pattern = re.compile(r'(r:id=")(' + "|".join(re.escape(k) for k in mapping) + r')"')
    return pattern.sub(lambda m: f'{m.group(1)}{mapping[m.group(2)]}"', text).encode("utf-8")


def _content_type(name: str) -> str:
    if name.endswith(".xlsx"):
        return _XLSX
    raise ValueError(f"no content type for {name}")
