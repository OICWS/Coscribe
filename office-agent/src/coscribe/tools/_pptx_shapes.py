"""Shapes on a slide addressed through groups: by index, by path (`"3/1"`, the second shape of
the group at index 3) or by name (a deck built from pages names its groups after the page's
`id`s).

A shape inside a group stores its position in the group's own child coordinates, which a group
can scale (`chOff`/`chExt` against `off`/`ext`); the tools speak slide inches, so positions go
through every enclosing group's transform both ways.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterator
from typing import Any

# An index, a path through groups, or a shape's name.
ShapeRef = int | str
PATH = re.compile(r"\d+(/\d+)*")
_A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
_P = "{http://schemas.openxmlformats.org/presentationml/2006/main}"
_EMU_PER_INCH = 914400


def walk(shapes: Any, prefix: str = "") -> Iterator[tuple[str, Any]]:
    """Every shape on the slide, groups' members included, with its path."""
    for index, shape in enumerate(shapes):
        path = f"{prefix}{index}"
        yield path, shape
        if _is_group(shape):
            yield from walk(shape.shapes, f"{path}/")


def find_shape(slide: Any, slide_number: int, ref: ShapeRef) -> Any:
    """The shape `ref` names: an index or a path, or a name used by one shape only."""
    text = str(ref).strip()
    if PATH.fullmatch(text):
        shapes, shape = slide.shapes, None
        for step in text.split("/"):
            members = list(shapes) if shapes is not None else []
            if not 0 <= int(step) < len(members):
                raise ValueError(
                    f"shape_index {text!r} out of range: slide {slide_number} has "
                    f"{len(members)} shape(s) at that level -- call list_pptx_shapes first."
                )
            shape = members[int(step)]
            shapes = shape.shapes if _is_group(shape) else None
        return shape
    named = [(path, shape) for path, shape in walk(slide.shapes) if shape.name == text]
    if len(named) == 1:
        return named[0][1]
    if not named:
        raise ValueError(
            f"No shape named {text!r} on slide {slide_number} -- call list_pptx_shapes for "
            f"the names and paths."
        )
    paths = ", ".join(path for path, _ in named)
    raise ValueError(
        f"{len(named)} shapes are named {text!r} on slide {slide_number} (paths {paths}); "
        f"give the path instead."
    )


def describe_members(
    group: Any, path: str, describe: Callable[[int, Any], dict[str, object]]
) -> list[dict[str, object]]:
    """`list_pptx_shapes`' entries for a group's members, by path, placed on the slide."""
    members = []
    for index, shape in enumerate(group.shapes):
        info = describe(index, shape)
        del info["index"]
        member_path = f"{path}/{index}"
        left, top, width, height = slide_box(shape)
        info.update(
            left_in=round(left / _EMU_PER_INCH, 2),
            top_in=round(top / _EMU_PER_INCH, 2),
            width_in=round(width / _EMU_PER_INCH, 2),
            height_in=round(height / _EMU_PER_INCH, 2),
        )
        if _is_group(shape):
            info["members"] = describe_members(shape, member_path, describe)
        members.append({"path": member_path, **info})
    return members


def in_group(shape: Any) -> bool:
    return bool(shape.element.getparent().tag == f"{_P}grpSp")


def slide_box(shape: Any) -> tuple[int, int, int, int]:
    """The shape's left, top, width and height on the slide, in EMU."""
    left, top = shape.left or 0, shape.top or 0
    width, height = shape.width or 0, shape.height or 0
    for group in _groups_around(shape):
        (off_x, off_y), (scale_x, scale_y), (ch_x, ch_y) = _transform(group)
        left, top = off_x + (left - ch_x) * scale_x, off_y + (top - ch_y) * scale_y
        width, height = width * scale_x, height * scale_y
    return round(left), round(top), round(width), round(height)


def set_slide_box(
    shape: Any,
    left: float | None = None,
    top: float | None = None,
    width: float | None = None,
    height: float | None = None,
) -> None:
    """Move or resize the shape to a slide position given in EMU; None keeps that value."""
    for group in reversed(_groups_around(shape)):
        (off_x, off_y), (scale_x, scale_y), (ch_x, ch_y) = _transform(group)
        left = None if left is None else ch_x + (left - off_x) / scale_x
        top = None if top is None else ch_y + (top - off_y) / scale_y
        width = None if width is None else width / scale_x
        height = None if height is None else height / scale_y
    if left is not None:
        shape.left = round(left)
    if top is not None:
        shape.top = round(top)
    if width is not None:
        shape.width = round(width)
    if height is not None:
        shape.height = round(height)


def _is_group(shape: Any) -> bool:
    return bool(shape.element.tag == f"{_P}grpSp")


def _groups_around(shape: Any) -> list[Any]:
    """The `<p:grpSp>` elements holding the shape, innermost first."""
    groups = []
    parent = shape.element.getparent()
    while parent is not None and parent.tag == f"{_P}grpSp":
        groups.append(parent)
        parent = parent.getparent()
    return groups


def _transform(group: Any) -> tuple[tuple[int, int], tuple[float, float], tuple[int, int]]:
    xfrm = group.find(f"{_P}grpSpPr/{_A}xfrm")
    if xfrm is None:
        return (0, 0), (1.0, 1.0), (0, 0)

    def pair(tag: str, x: str, y: str, default: int) -> tuple[int, int]:
        node = xfrm.find(f"{_A}{tag}")
        if node is None:
            return default, default
        return int(node.get(x, default)), int(node.get(y, default))

    off, ext = pair("off", "x", "y", 0), pair("ext", "cx", "cy", 0)
    ch_off, ch_ext = pair("chOff", "x", "y", 0), pair("chExt", "cx", "cy", 0)
    scale = tuple(e / c if c else 1.0 for e, c in zip(ext, ch_ext, strict=True))
    return off, (scale[0], scale[1]), ch_off
