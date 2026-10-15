"""Compile a deck's page sources (SVG) into a .pptx made of native, editable shapes.

The page sources are the deck's source of truth (decision 0010): a model writes each page as one
SVG in the subset the copied emitter (`tools/_native_svg/`) converts, and an edit recompiles the
pages it touched. This walks each page, hands every element to the emitter and packages the
slides with python-pptx. Errors are collected per page instead of stopping, because the caller
sends them back to the model to repair the pages named in the report.
"""

from __future__ import annotations

import io
import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

from lxml import etree
from pptx import Presentation
from pptx.opc.constants import RELATIONSHIP_TYPE as RT
from pptx.util import Emu

from ...._native_svg import pptx_effects
from ...._native_svg.svg_to_pptx import geometry_properties, tspan_flattener
from ...._native_svg.svg_to_pptx.drawingml import elements, paths, text_properties, utils
from ...._native_svg.svg_to_pptx.drawingml.context import ConvertContext, ShapeResult
from ...._native_svg.svg_to_pptx.drawingml.styles import build_effect_xml, get_element_opacity
from . import native
from .icons import expand_icons
from .template import Example, canvas, layout, open_template, renumber, start_from

SVG_NS = "http://www.w3.org/2000/svg"
EMU_PER_PX = utils.EMU_PER_PX
_NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
}
_NSDECL = " ".join(f'xmlns:{k}="{v}"' for k, v in _NS.items())
TITLE_ID = "title"

_CONVERTERS: dict[str, Callable[[ET.Element, ConvertContext], ShapeResult | None]] = {
    "rect": elements.convert_rect,
    "circle": elements.convert_circle,
    "ellipse": elements.convert_ellipse,
    "line": elements.convert_line,
    "path": elements.convert_path,
    "polygon": elements.convert_polygon,
    "polyline": elements.convert_polyline,
    "text": elements.convert_text,
    "image": elements.convert_image,
}
_NON_VISUAL = {
    "defs",
    "title",
    "desc",
    "metadata",
    "linearGradient",
    "radialGradient",
    "filter",
    "clipPath",
    "marker",
    "symbol",
}
_TRANSLATE_SCALE = re.compile(
    r"\s*(?:translate\(\s*(?P<tx>[-\d.e]+)(?:[\s,]+(?P<ty>[-\d.e]+))?\s*\))?"
    r"\s*(?:scale\(\s*(?P<sx>[-\d.e]+)(?:[\s,]+(?P<sy>[-\d.e]+))?\s*\))?\s*"
)

# Upstream's converter preflight, minus its project-only checks (templates, formulas, icons):
# what the emitter would otherwise convert wrongly or reject element by element.
_PAGE_CHECKS: tuple[Callable[[ET.Element], list[str]], ...] = (
    utils.project_geometry_length_errors,
    text_properties.project_text_property_errors,
    paths.project_freeform_geometry_errors,
    utils.project_stroke_style_errors,
    utils.project_opacity_errors,
    utils.project_paint_errors,
    utils.project_mask_errors,
    utils.project_definition_errors,
    utils.project_paint_reference_errors,
    utils.project_marker_errors,
    utils.project_gradient_errors,
    paths.project_gradient_geometry_errors,
    pptx_effects.project_effect_status_errors,
    utils.project_filter_errors,
    utils.project_image_aspect_ratio_errors,
    utils.project_transform_errors,
    elements.project_clip_path_errors,
    elements.project_nested_svg_crop_errors,
)


@dataclass
class PageReport:
    name: str
    shapes: int = 0
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class CompileReport:
    path: Path
    pages: list[PageReport]

    @property
    def ok(self) -> bool:
        return all(not page.errors for page in self.pages)

    def errors(self) -> list[str]:
        return [f"{page.name}: {e}" for page in self.pages for e in page.errors]


def compile_pages(
    pages: Sequence[tuple[str, str]],
    out: Path,
    *,
    resource_root: Path | None = None,
    svg_dir: Path | None = None,
    template: Path | None = None,
) -> CompileReport:
    """Write `out` from `(name, svg_text)` pages, one slide each, in order.

    An image's href is resolved against `svg_dir` (default `resource_root`), the folder the
    pages are in; an image outside `resource_root` is an error. With `template` (the user's
    .pptx) the slides are made from its layouts and every page's viewBox is its slide size.
    The deck is written even when pages have errors (their failing elements are left out), so
    a preview can show what the repair has to fix.
    """
    prs, examples = open_template(template) if template is not None else (Presentation(), [])
    reports: list[PageReport] = []
    size: tuple[int, int] | None = canvas(prs) if template is not None else None
    for name, svg_text in pages:
        report = PageReport(name)
        reports.append(report)
        try:
            root = ET.fromstring(svg_text)
        except ET.ParseError as e:
            report.errors.append(f"not well-formed XML: {e}")
            prs.slides.add_slide(layout(prs, None))
            continue
        width, height = _canvas(root, report)
        if size is None:
            size = (width, height)
            prs.slide_width, prs.slide_height = Emu(width * EMU_PER_PX), Emu(height * EMU_PER_PX)
        elif (width, height) != size:
            report.errors.append(
                f"canvas {width}x{height} differs from the deck's {size[0]}x{size[1]}"
            )
        _compile_page(prs, root, report, resource_root, svg_dir or resource_root, examples)
    out.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(out))
    return CompileReport(out, reports)


def _canvas(root: ET.Element, report: PageReport) -> tuple[int, int]:
    box = (root.get("viewBox") or "").replace(",", " ").split()
    try:
        x, y, w, h = (float(v) for v in box)
    except ValueError:
        report.errors.append('the root needs viewBox="0 0 W H"')
        return 1280, 720
    if (x, y) != (0, 0) or w <= 0 or h <= 0 or not (w.is_integer() and h.is_integer()):
        report.errors.append(f"viewBox must be 0 0 W H with positive whole pixels, got {box}")
    return int(w), int(h)


def _compile_page(
    prs: Any,
    root: ET.Element,
    report: PageReport,
    resource_root: Path | None,
    svg_dir: Path | None,
    examples: list[Example],
) -> None:
    example = _example(root, examples, report)
    try:
        chosen = example.layout if example else layout(prs, root.get("data-layout"))
    except ValueError as e:
        report.errors.append(str(e))
        chosen = layout(prs, None)
    slide = prs.slides.add_slide(chosen)
    for placeholder in list(slide.placeholders):
        placeholder.element.getparent().remove(placeholder.element)
    copied = start_from(slide, example) if example is not None else []
    if example is not None and example.dropped:
        report.warnings.append(
            f"left out of example slide {root.get('data-template-slide')}: "
            f"{', '.join(example.dropped)} (a chart, SmartArt, media or a link to a slide "
            "cannot be copied; draw it on the page if the deck needs it)"
        )
    report.errors.extend(expand_icons(root))
    try:
        geometry_properties.materialize_inline_geometry_properties(root)
    except Exception as e:  # reported to the model, not raised
        report.errors.append(f"inline geometry: {e}")
    for check in _PAGE_CHECKS:
        report.errors.extend(check(root))
    if svg_dir is not None:
        report.errors.extend(
            elements.project_image_errors(root, svg_dir, resource_root=resource_root)
        )
    tree = ET.ElementTree(root)
    tspan_flattener.flatten_positional_tspans(
        tree, merge_paragraphs=True, preserve_line_breaks=True
    )

    defs, _duplicates = utils.project_definition_index(root)
    ctx = ConvertContext(
        defs=defs,
        svg_dir=svg_dir,
        resource_root=resource_root,
        inherited_styles=utils._extract_inheritable_styles(root),
        viewport_width=float(prs.slide_width) / EMU_PER_PX,
        viewport_height=float(prs.slide_height) / EMU_PER_PX,
        # Far above python-pptx's own numbering, so a relationship left unmapped by
        # `_attach_relationships` points nowhere and fails instead of hitting another part.
        rel_id_counter=1000,
    )
    background = _promote_background(root)
    shapes: list[str] = []
    for child in root:
        result = _convert(child, ctx, report)
        if result is not None:
            shapes.append(result.xml)
    shapes = _attach_relationships(slide, ctx, shapes, report)

    sp_tree = slide.shapes._spTree
    for xml in shapes:
        for element in etree.fromstring(f"<p:wrap {_NSDECL}>{xml}</p:wrap>"):
            sp_tree.append(element)
            report.shapes += 1
    if background is not None:
        for previous in slide._element.cSld.findall(f"{{{_NS['p']}}}bg"):
            previous.getparent().remove(previous)
        slide._element.cSld.insert(0, etree.fromstring(background))
    renumber(slide, copied)
    _make_title_placeholder(sp_tree, report)
    notes = _notes(root)
    if notes:
        slide.notes_slide.notes_text_frame.text = "\n".join(notes)


def _notes(root: ET.Element) -> list[str]:
    """The speaker notes a page carries in a top-level `<desc id="notes">`, one paragraph per
    line: a line the model wrapped inside a paragraph cannot be told from a new one, and joining
    Chinese lines with a space would put a space in a sentence."""
    for child in root:
        if _local(child) == "desc" and child.get("id") == "notes":
            return [line.strip() for line in "".join(child.itertext()).splitlines() if line.strip()]
    return []


def _example(root: ET.Element, examples: list[Example], report: PageReport) -> Example | None:
    """The template slide the page starts from (`data-template-slide`, 1-based), if any."""
    wanted = root.get("data-template-slide")
    if wanted is None:
        return None
    if not examples:
        report.errors.append("data-template-slide needs a template")
        return None
    if not wanted.isdigit() or not 1 <= int(wanted) <= len(examples):
        report.errors.append(
            f"data-template-slide {wanted!r}: the template has {len(examples)} slides"
        )
        return None
    return examples[int(wanted) - 1]


def _local(elem: ET.Element) -> str:
    return elem.tag.replace(f"{{{SVG_NS}}}", "")


def _convert(elem: ET.Element, ctx: ConvertContext, report: PageReport) -> ShapeResult | None:
    tag = _local(elem)
    if tag in _NON_VISUAL:
        return None
    label = f'<{tag} id="{elem.get("id")}">' if elem.get("id") else f"<{tag}>"
    if tag == "g" and native.native_kind(elem):
        try:
            return native.convert(elem, ctx)
        except Exception as e:  # reported like any element's error
            report.errors.append(f"{label}: {e}")
            return None
    if tag == "g":
        return _convert_group(elem, ctx, report)
    converter = _CONVERTERS.get(tag)
    if converter is None:
        report.errors.append(f"{label} is not supported")
        return None
    try:
        return converter(elem, ctx)
    except Exception as e:  # one bad element must not hide the rest of the page
        report.errors.append(f"{label}: {e}")
        return None


def _convert_group(elem: ET.Element, ctx: ConvertContext, report: PageReport) -> ShapeResult | None:
    transform = elem.get("transform", "")
    match = _TRANSLATE_SCALE.fullmatch(transform)
    if match is None:
        report.errors.append(
            f'<g id="{elem.get("id")}"> transform "{transform}": a group takes translate() and '
            "scale() only; put rotation on the child elements"
        )
        return None
    tx, ty = float(match["tx"] or 0), float(match["ty"] or 0)
    sx = float(match["sx"] or 1)
    sy = float(match["sy"] or match["sx"] or 1)
    filter_id = utils.resolve_url_id(elem.get("filter", ""))
    opacity = get_element_opacity(elem)
    child_ctx = ctx.child(
        dx=tx * ctx.scale_x,
        dy=ty * ctx.scale_y,
        sx=sx,
        sy=sy,
        filter_id=filter_id or ctx.filter_id,
        style_overrides=utils._extract_inheritable_styles(elem),
        opacity_multiplier=1.0 if opacity is None else opacity,
    )
    child_ctx.depth = ctx.depth + 1
    results = [r for r in (_convert(child, child_ctx, report) for child in elem) if r is not None]
    # The child numbers relationships and shape ids from its own copy of the counters; without
    # this, pictures in two sibling groups both get rId2 and show the same image.
    ctx.sync_from_child(child_ctx)
    if not results:
        return None
    if len(results) == 1 and not elem.get("id"):
        return results[0]
    boxes = [r.bounds_emu for r in results if r.bounds_emu is not None]
    if not boxes:
        return ShapeResult(xml="\n".join(r.xml for r in results))
    x0, y0 = min(b[0] for b in boxes), min(b[1] for b in boxes)
    w = max(max(b[2] for b in boxes) - x0, 1)
    h = max(max(b[3] for b in boxes) - y0, 1)
    group_id = ctx.next_id()
    effect = (
        build_effect_xml(ctx.defs[filter_id], child_ctx.opacity_multiplier)
        if filter_id and filter_id in ctx.defs
        else ""
    )
    name = _xml_attr(elem.get("id") or f"Group {group_id}")
    xml = (
        f'<p:grpSp><p:nvGrpSpPr><p:cNvPr id="{group_id}" name="{name}"/><p:cNvGrpSpPr/><p:nvPr/>'
        f'</p:nvGrpSpPr><p:grpSpPr><a:xfrm><a:off x="{x0}" y="{y0}"/><a:ext cx="{w}" cy="{h}"/>'
        f'<a:chOff x="{x0}" y="{y0}"/><a:chExt cx="{w}" cy="{h}"/></a:xfrm>{effect}</p:grpSpPr>'
        + "\n".join(r.xml for r in results)
        + "</p:grpSp>"
    )
    return ShapeResult(xml=xml, bounds_emu=(x0, y0, x0 + w, y0 + h))


def _xml_attr(value: str) -> str:
    return value.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;")


def _promote_background(root: ET.Element) -> str | None:
    """A full-canvas solid rectangle drawn first becomes the slide background, as PowerPoint's
    own "Format Background" would: it is then not a shape the user can select by accident."""
    first = next((c for c in root if _local(c) not in _NON_VISUAL), None)
    if first is None or _local(first) != "rect" or first.get("transform"):
        return None
    box = root.get("viewBox", "").split()
    if len(box) != 4:
        return None
    full = (first.get("x", "0"), first.get("y", "0"), first.get("width"), first.get("height"))
    if tuple(float(v or "nan") for v in full) != tuple(float(v) for v in box):
        return None
    fill = first.get("fill", "")
    if not re.fullmatch(r"#[0-9A-Fa-f]{6}", fill) or first.get("rx") or first.get("stroke"):
        return None
    root.remove(first)
    return (
        f'<p:bg {_NSDECL}><p:bgPr><a:solidFill><a:srgbClr val="{fill[1:].upper()}"/>'
        "</a:solidFill><a:effectLst/></p:bgPr></p:bg>"
    )


def _attach_relationships(
    slide: Any, ctx: ConvertContext, shapes: list[str], report: PageReport
) -> list[str]:
    """Give each image and link the emitter referenced a real relationship on this slide.

    The emitter numbers relationships itself (`rId2`, ...); python-pptx owns the slide's
    relationships, so each upstream id is mapped to the id python-pptx assigns."""
    mapping: dict[str, str] = {}
    for entry in ctx.rel_entries:
        target = entry["target"]
        if entry["type"] == RT.IMAGE:
            data = ctx.media_files.get(target.rsplit("/", 1)[-1])
            if data is None:
                report.errors.append(f"image data missing for {target}")
                continue
            _part, new_id = slide.part.get_or_add_image_part(io.BytesIO(data))
        elif entry["type"] == RT.HYPERLINK and entry.get("target_mode") == "External":
            new_id = slide.part.relate_to(target, RT.HYPERLINK, is_external=True)
        elif entry["type"].endswith("/chart") or entry["type"].endswith("/chartEx"):
            new_id = slide.part.relate_to(native.add_part(slide, ctx, target), entry["type"])
        else:
            kind = entry["type"].rsplit("/", 1)[-1]
            report.warnings.append(f"relationship {kind} not supported yet")
            continue
        mapping[entry["id"]] = new_id
    if not mapping:
        return shapes
    pattern = re.compile(r'(r:(?:embed|id|link)=")(' + "|".join(map(re.escape, mapping)) + r')"')
    return [pattern.sub(lambda m: f'{m.group(1)}{mapping[m.group(2)]}"', xml) for xml in shapes]


def _make_title_placeholder(sp_tree: Any, report: PageReport) -> None:
    """The text with id "title" becomes the slide's title placeholder, so PowerPoint's outline,
    accessibility checker and `edit_pptx_text` find the page title. A placeholder cannot sit in
    a group, so a title inside one is moved out to the top level, in front of its group."""
    named = sp_tree.xpath(f'.//p:sp[p:nvSpPr/p:cNvPr/@name="{TITLE_ID}"][p:txBody]')
    if not named:
        report.warnings.append('no <text id="title">: the slide has no title for the outline')
        return
    title = named[0]
    parent = title.getparent()
    if parent is not sp_tree:
        top = parent
        while top.getparent() is not sp_tree:
            top = top.getparent()
        top.addnext(title)
    nv = title.find("p:nvSpPr", _NS)
    c_nv_sp_pr = nv.find("p:cNvSpPr", _NS)
    c_nv_sp_pr.attrib.pop("txBox", None)
    etree.SubElement(c_nv_sp_pr, f"{{{_NS['a']}}}spLocks", noGrp="1")
    nv_pr = nv.find("p:nvPr", _NS)
    etree.SubElement(nv_pr, f"{{{_NS['p']}}}ph", type="title")
