"""One shape's look copied onto others, as PowerPoint's Format Painter does: size, outline
shape, fill, line and text format. A request to make boxes "match" another one otherwise goes
through a script that rewrites whatever it touches; here each named part is copied exactly and
nothing else on the slide changes."""

from __future__ import annotations

import copy
from typing import Any

from ..._file_locks import locked_by_path
from ..._ooxml_validate import assert_ooxml_valid
from . import toolkit_helpers as th
from .shape_description import describe_shape
from .toolkit_base import ToolkitBase

_A = "http://schemas.openxmlformats.org/drawingml/2006/main"
_P = "http://schemas.openxmlformats.org/presentationml/2006/main"
PARTS = ("size", "shape", "fill", "line", "text")
_GEOMETRY = ("prstGeom", "custGeom")
_FILLS = ("noFill", "solidFill", "gradFill", "blipFill", "pattFill", "grpFill")
# spPr's children in schema order; a copied part goes before the first later one.
_SPPR_ORDER = (
    "xfrm",
    *_GEOMETRY,
    *_FILLS,
    "ln",
    "effectLst",
    "effectDag",
    "scene3d",
    "sp3d",
    "extLst",
)
_RUN_ATTRS = ("sz", "b", "i", "u", "strike", "spc", "cap", "baseline")
_RUN_CHILDREN = ("ln", *_FILLS, "effectLst", "highlight", "latin", "ea", "cs", "sym")
_RUN_ORDER = (
    *_RUN_CHILDREN[:-4],
    "uLnTx",
    "uLn",
    "uFillTx",
    "uFill",
    *_RUN_CHILDREN[-4:],
    "hlinkClick",
    "hlinkMouseOver",
    "rtl",
    "extLst",
)
_BODY_ATTRS = ("anchor", "anchorCtr", "lIns", "tIns", "rIns", "bIns", "wrap", "vert")


def _q(ns: str, tag: str) -> str:
    return f"{{{ns}}}{tag}"


def _local(element: Any) -> str:
    return str(element.tag).rsplit("}", 1)[-1]


def _place(parent: Any, element: Any, order: tuple[str, ...]) -> None:
    """Insert `element` where the schema wants it among `parent`'s children."""
    rank = order.index(_local(element))
    for index, child in enumerate(parent):
        if _local(child) in order and order.index(_local(child)) > rank:
            parent.insert(index, element)
            return
    parent.append(element)


def _replace(source: Any, target: Any, names: tuple[str, ...], order: tuple[str, ...]) -> None:
    for child in [c for c in target if _local(c) in names]:
        target.remove(child)
    for child in [c for c in source if _local(c) in names]:
        _place(target, copy.deepcopy(child), order)


def _sp_pr(shape: Any) -> Any:
    found = shape._element.find(_q(_P, "spPr"))
    if found is None:
        raise ValueError(f"{shape.name!r} has no shape properties to copy (a picture or a table?)")
    return found


def _copy_style(source: Any, target: Any) -> None:
    """The theme style a shape without its own fill or line draws with comes along, so a box
    styled by the theme does not turn plain when its look is copied."""
    old, new = target._element.find(_q(_P, "style")), source._element.find(_q(_P, "style"))
    if new is None:
        return
    if old is not None:
        target._element.remove(old)
    target._element.find(_q(_P, "spPr")).addnext(copy.deepcopy(new))


def _first_run_props(shape: Any) -> tuple[Any, Any, Any]:
    body = shape._element.find(f".//{_q(_P, 'txBody')}")
    if body is None:
        raise ValueError(f"{shape.name!r} has no text whose format could be copied")
    runs = body.findall(f".//{_q(_A, 'rPr')}")
    props = runs[0] if runs else body.find(f".//{_q(_A, 'endParaRPr')}")
    paragraph = body.find(f".//{_q(_A, 'pPr')}")
    return body.find(_q(_A, "bodyPr")), paragraph, props


def _copy_text(source: Any, target: Any) -> None:
    body, paragraph, props = _first_run_props(source)
    target_body = target._element.find(f".//{_q(_P, 'txBody')}")
    if target_body is None:
        return
    target_body_pr = target_body.find(_q(_A, "bodyPr"))
    if body is not None and target_body_pr is not None:
        for name in _BODY_ATTRS:
            value = body.get(name)
            if value is None:
                target_body_pr.attrib.pop(name, None)
            else:
                target_body_pr.set(name, value)
        fits = ("noAutofit", "normAutofit", "spAutoFit")
        _replace(body, target_body_pr, fits, (*fits, "scene3d", "sp3d", "flatTx", "extLst"))
    for target_paragraph in target_body.findall(_q(_A, "p")):
        align = paragraph.get("algn") if paragraph is not None else None
        p_pr = target_paragraph.find(_q(_A, "pPr"))
        if align is not None:
            if p_pr is None:
                p_pr = target_paragraph.makeelement(_q(_A, "pPr"), {})
                target_paragraph.insert(0, p_pr)
            p_pr.set("algn", align)
        elif p_pr is not None:
            p_pr.attrib.pop("algn", None)
        if props is None:
            continue
        for run_props in target_paragraph.iter(_q(_A, "rPr"), _q(_A, "endParaRPr")):
            for name in _RUN_ATTRS:
                value = props.get(name)
                if value is None:
                    run_props.attrib.pop(name, None)
                else:
                    run_props.set(name, value)
            _replace(props, run_props, _RUN_CHILDREN, _RUN_ORDER)
        for run in target_paragraph.findall(_q(_A, "r")):
            if run.find(_q(_A, "rPr")) is None:
                run_props = copy.deepcopy(props)
                run_props.tag = _q(_A, "rPr")
                run.insert(0, run_props)


def match_format(source: Any, target: Any, parts: tuple[str, ...]) -> None:
    """Copy `parts` of `source`'s look onto `target`, leaving everything else as it is."""
    if "size" in parts:
        target.width, target.height = source.width, source.height
    if {"shape", "fill", "line"} & set(parts):
        source_pr, target_pr = _sp_pr(source), _sp_pr(target)
        if "shape" in parts:
            _replace(source_pr, target_pr, _GEOMETRY, _SPPR_ORDER)
        if "fill" in parts or "line" in parts:
            _copy_style(source, target)
        if "fill" in parts:
            _replace(source_pr, target_pr, _FILLS, _SPPR_ORDER)
        if "line" in parts:
            _replace(source_pr, target_pr, ("ln",), _SPPR_ORDER)
    if "text" in parts:
        _copy_text(source, target)


class FormatMatchMixin(ToolkitBase):
    @locked_by_path
    def match_pptx_shape_format(
        self,
        path: str,
        slide: int,
        source: str,
        targets: list[str],
        parts: list[str] | None = None,
    ) -> dict[str, object]:
        chosen = tuple(parts or PARTS)
        unknown = sorted(set(chosen) - set(PARTS))
        if unknown:
            raise ValueError(f"parts {unknown} are not among {list(PARTS)}")
        if not targets:
            raise ValueError("Name at least one target shape.")
        prs, file_path, target_slide = self._open_slide(path, slide)
        model = th.get_shape_at_index(target_slide, slide, source)
        shapes = [(t, th.get_shape_at_index(target_slide, slide, t)) for t in targets]
        if any(shape._element is model._element for _, shape in shapes):
            raise ValueError("The source is among the targets; name the shapes to change only.")
        for _, shape in shapes:
            match_format(model, shape, chosen)
        assert_ooxml_valid(target_slide.element, "match_pptx_shape_format")
        prs.save(str(file_path))
        return {
            "path": self._scope.relative(file_path),
            "slide": slide,
            "copied": list(chosen),
            "source": describe_shape(source, model),
            "targets": [describe_shape(t, shape) for t, shape in shapes],
        }
