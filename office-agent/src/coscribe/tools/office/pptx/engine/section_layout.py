"""Containers in a section (decision 0018): an `<x-stack>` holds elements and places them, in a
row or a column, with a gap, padding, alignment and the look of a card. It is laid out here, once,
into the plain positioned elements every other part of the engine already reads, so the compiled
deck holds no containers and the app's drawing and the deck agree.

A child has no `left` or `top`. Along the container's direction it takes `width` or `height`, or
a share of the room (`flex-grow`, `flex-shrink`, `flex-basis`); across it, `height` or `width`,
or the container's room (`align: stretch`). Text in a column takes the height its words need.
"""

from __future__ import annotations

import copy
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from xml.etree import ElementTree as ET

STACK = "x-stack"
_PX = re.compile(r"(-?\d+(?:\.\d+)?)(?:px)?")
_FLEX = ("flex-grow", "flex-shrink", "flex-basis")
_PLACED = {"left", "top", "width", "height", *_FLEX}
_LOOK = ("background", "border", "border-radius", "opacity", "box-shadow")
_STACK_STYLES = {*_PLACED, "gap", "padding", "align", "justify", *_LOOK}
_ALIGN = ("start", "center", "end", "stretch")
_JUSTIFY = ("start", "center", "end", "between")
_TEXT = frozenset({"h1", "h2", "h3", "p", "ul", "ol"})
_MAX_DEPTH = 6

# Height in px of a text element placed at `width` with the given declared styles; supplied by
# the section reader, which knows the fonts.
Measure = Callable[[ET.Element, dict[str, str], float], float]


class LayoutError(ValueError):
    """A container that cannot be laid out; the section reader reports it as the section's own."""


def local(elem: ET.Element) -> str:
    return elem.tag.rsplit("}", 1)[-1] if isinstance(elem.tag, str) else ""


def _name(elem: ET.Element) -> str:
    return f'<{local(elem)} id="{elem.get("id")}">' if elem.get("id") else f"<{local(elem)}>"


Path = tuple[int, ...]


@dataclass
class Laid:
    """What the layout made of the section's tree, by each element's path: its index among its
    parent's elements (the section's, notes left out), then down through the containers."""

    leaf: dict[Path, ET.Element] = field(default_factory=dict)
    # A container's box, and the rectangle of its look when it has one.
    boxes: dict[Path, tuple[float, float, float, float]] = field(default_factory=dict)
    looks: dict[Path, ET.Element] = field(default_factory=dict)


def expand_stacks(root: ET.Element, measure: Measure) -> Laid:
    """Replaces each `<x-stack>` child of the section by the elements it lays out, in place."""
    laid = Laid()
    tops = [c for c in root if isinstance(c.tag, str) and local(c) != "aside"]
    for index, child in enumerate(tops):
        if local(child) != STACK:
            laid.leaf[(index,)] = child
            continue
        decl = _declarations(child, _STACK_STYLES)
        box = [_px(child, decl, name) for name in ("left", "top", "width", "height")]
        x, y, w, h = box
        if x is None or y is None or w is None or h is None or w <= 0 or h <= 0:
            raise LayoutError(
                f"{_name(child)}: a container on the slide needs left, top, width and height"
            )
        _, placed = _place(child, x, y, w, h, measure, 0, (index,), laid)
        at = list(root).index(child)
        root.remove(child)
        for offset, elem in enumerate(placed):
            root.insert(at + offset, elem)
    return laid


def _declarations(elem: ET.Element, allowed: set[str] | None = None) -> dict[str, str]:
    found: dict[str, str] = {}
    for declaration in (elem.get("style") or "").split(";"):
        if not declaration.strip():
            continue
        name, sep, value = declaration.partition(":")
        name = name.strip().lower()
        if not sep:
            raise LayoutError(f"{_name(elem)}: {declaration.strip()!r} is not a style")
        if allowed is not None and name not in allowed:
            raise LayoutError(f"{_name(elem)}: style {name!r} is not allowed on a container")
        found[name] = value.strip()
    return found


def _px(elem: ET.Element, decl: dict[str, str], name: str) -> float | None:
    raw = decl.get(name)
    if raw is None:
        return None
    match = _PX.fullmatch(raw)
    if match is None:
        raise LayoutError(f"{_name(elem)}: {name} must be a number of px, got {raw!r}")
    return float(match.group(1))


def _number(elem: ET.Element, decl: dict[str, str], name: str, default: float) -> float:
    value = _px(elem, decl, name)
    if value is not None and value < 0:
        raise LayoutError(f"{_name(elem)}: {name} cannot be negative")
    return default if value is None else value


def _choice(
    elem: ET.Element, decl: dict[str, str], name: str, options: tuple[str, ...], default: str
) -> str:
    value = decl.get(name, default).strip().lower()
    if value not in options:
        raise LayoutError(f"{_name(elem)}: {name} is one of {', '.join(options)}, got {value!r}")
    return value


class _Child:
    """One element of a container: what it declares, and the size it ends up with."""

    def __init__(self, elem: ET.Element, row: bool) -> None:
        self.elem = elem
        self.stack = local(elem) == STACK
        self.decl = _declarations(elem, _STACK_STYLES if self.stack else None)
        self.grow = _number(elem, self.decl, "flex-grow", 0.0)
        self.shrink = _number(elem, self.decl, "flex-shrink", 1.0)
        main, cross = ("width", "height") if row else ("height", "width")
        self.fixed_main = _px(elem, self.decl, main)
        self.fixed_cross = _px(elem, self.decl, cross)
        self.basis = _px(elem, self.decl, "flex-basis")
        if self.basis is None:
            self.basis = self.fixed_main
        self.main = 0.0
        self.cross = 0.0
        # Sized by its content (text, a container with no height): it never shrinks below it.
        self.hug = False


def _place(
    stack: ET.Element,
    x: float,
    y: float,
    w: float,
    h: float | None,
    measure: Measure,
    depth: int,
    path: Path = (),
    laid: Laid | None = None,
) -> tuple[float, list[ET.Element]]:
    """The container at (x, y), `w` wide and `h` tall (None: as tall as its content needs):
    its height, and the elements it comes to, its own look first so the children sit over it."""
    if depth > _MAX_DEPTH:
        raise LayoutError(f"{_name(stack)}: containers nest {_MAX_DEPTH} deep at most")
    for name in stack.attrib:
        if name not in {"id", "style", "data-layout"}:
            raise LayoutError(f"{_name(stack)}: attribute {name!r} is not allowed")
    decl = _declarations(stack, _STACK_STYLES)
    if stack.get("data-layout", "column") not in {"row", "column"}:
        raise LayoutError(f"{_name(stack)}: data-layout is row or column")
    row = stack.get("data-layout", "column") == "row"
    gap = _number(stack, decl, "gap", 0.0)
    pad = _number(stack, decl, "padding", 0.0)
    align = _choice(stack, decl, "align", _ALIGN, "stretch")
    justify = _choice(stack, decl, "justify", _JUSTIFY, "start")
    kids = [_Child(k, row) for k in stack if isinstance(k.tag, str)]
    if (stack.text or "").strip() or any((k.tail or "").strip() for k in stack):
        raise LayoutError(f"{_name(stack)} holds elements, not text; put a <p> in it")
    inner_w = w - 2 * pad
    inner_h = None if h is None else h - 2 * pad
    ctx = _Context(stack, row, align, justify, gap, inner_w, inner_h, measure, depth)
    ctx.path, ctx.laid = path, laid
    ctx.resolve(kids)
    height = h if h is not None else ctx.content_cross_or_main(kids) + 2 * pad
    out = _look(stack, decl, x, y, w, height)
    if laid is not None:
        laid.boxes[path] = (x, y, w, height)
        if out:
            laid.looks[path] = out[0]
    out += ctx.emit(kids, x + pad, y + pad)
    return height, out


class _Context:
    def __init__(
        self,
        stack: ET.Element,
        row: bool,
        align: str,
        justify: str,
        gap: float,
        inner_w: float,
        inner_h: float | None,
        measure: Measure,
        depth: int,
    ) -> None:
        self.stack, self.row, self.align, self.justify, self.gap = stack, row, align, justify, gap
        self.inner_w, self.inner_h, self.measure, self.depth = inner_w, inner_h, measure, depth
        self.leftover = 0.0
        self.path: Path = ()
        self.laid: Laid | None = None

    @property
    def main_room(self) -> float | None:
        return self.inner_w if self.row else self.inner_h

    @property
    def cross_room(self) -> float | None:
        return self.inner_h if self.row else self.inner_w

    def resolve(self, kids: list[_Child]) -> None:
        """Each child's main size (basis, then the room shared out) and cross size."""
        if not self.row:
            for k in kids:
                k.cross = self._cross_width(k)
        for k in kids:
            if k.basis is not None:
                k.main = k.basis
            elif k.grow > 0:
                k.main = 0.0
            elif self.row:
                raise LayoutError(f"{_name(k.elem)}: in a row it needs a width or flex-grow")
            else:
                k.main = self._content_height(k, k.cross)
                k.hug = True
        self._share_room(kids)
        for k in kids:
            if self.row:
                k.cross = self._cross_height(k)

    def _cross_width(self, k: _Child) -> float:
        if k.fixed_cross is not None:
            return k.fixed_cross
        return self.inner_w

    def _cross_height(self, k: _Child) -> float:
        if k.fixed_cross is not None:
            return k.fixed_cross
        if self.inner_h is not None and self.align == "stretch":
            return self.inner_h
        return self._content_height(k, k.main)

    def _content_height(self, k: _Child, width: float) -> float:
        """The height an element needs at `width`: text its words, a container its content."""
        if k.stack:
            return _place(k.elem, 0.0, 0.0, width, None, self.measure, self.depth + 1)[0]
        if local(k.elem) in _TEXT:
            return self.measure(k.elem, k.decl, width)
        height = _px(k.elem, k.decl, "height")
        if height is None:
            raise LayoutError(f"{_name(k.elem)}: it needs a height here")
        return height

    def _share_room(self, kids: list[_Child]) -> None:
        total_gap = self.gap * max(len(kids) - 1, 0)
        used = sum(k.main for k in kids) + total_gap
        room = self.main_room
        self.leftover = 0.0
        if room is None:
            return
        free = room - used
        if free > 0:
            weight = sum(k.grow for k in kids)
            if weight > 0:
                for k in kids:
                    k.main += free * k.grow / weight
                free = 0.0
        elif free < 0:
            weight = sum(k.shrink * k.main for k in kids if not k.hug)
            if weight > 0:
                for k in kids:
                    if not k.hug:
                        k.main = max(0.0, k.main + free * k.shrink * k.main / weight)
                free = 0.0
        self.leftover = max(free, 0.0)

    def content_cross_or_main(self, kids: list[_Child]) -> float:
        """The height a container with no height of its own needs."""
        if self.row:
            return max((k.cross for k in kids), default=0.0)
        return sum(k.main for k in kids) + self.gap * max(len(kids) - 1, 0)

    def emit(self, kids: list[_Child], x: float, y: float) -> list[ET.Element]:
        room_cross = self.cross_room
        offset, spacing = 0.0, self.gap
        if kids and self.leftover > 0:
            if self.justify == "center":
                offset = self.leftover / 2
            elif self.justify == "end":
                offset = self.leftover
            elif self.justify == "between" and len(kids) > 1:
                spacing += self.leftover / (len(kids) - 1)
        out: list[ET.Element] = []
        at = offset
        for j, k in enumerate(kids):
            span = k.cross
            if room_cross is None:
                room = max((c.cross for c in kids), default=0.0)
            else:
                room = room_cross
            shift = {"start": 0.0, "stretch": 0.0, "center": (room - span) / 2, "end": room - span}[
                self.align
            ]
            cx, cy = (x + at, y + shift) if self.row else (x + shift, y + at)
            cw, ch = (k.main, span) if self.row else (span, k.main)
            out += self._element(k, cx, cy, cw, ch, self.path + (j,))
            at += k.main + spacing
        return out

    def _element(
        self, k: _Child, x: float, y: float, w: float, h: float, path: Path
    ) -> list[ET.Element]:
        if k.stack:
            return _place(k.elem, x, y, w, h, self.measure, self.depth + 1, path, self.laid)[1]
        copy_ = copy.deepcopy(k.elem)
        copy_.set(
            "style", _style({n: v for n, v in k.decl.items() if n not in _PLACED}, x, y, w, h)
        )
        if self.laid is not None:
            self.laid.leaf[path] = copy_
        return [copy_]


def _style(rest: dict[str, str], x: float, y: float, w: float, h: float) -> str:
    box = {"left": x, "top": y, "width": w, "height": h}
    parts = [f"{n}:{round(v, 2):g}px" for n, v in box.items()]
    parts += [f"{n}:{v}" for n, v in rest.items()]
    return ";".join(parts)


def _look(
    stack: ET.Element, decl: dict[str, str], x: float, y: float, w: float, h: float
) -> list[ET.Element]:
    """The container's card: a rectangle behind its children, when it has any look of its own."""
    look = {n: decl[n] for n in _LOOK if n in decl}
    if not look:
        return []
    shape = ET.Element(
        "x-shape", {"data-shape": "round-rect" if "border-radius" in look else "rect"}
    )
    if stack.get("id"):
        shape.set("id", stack.get("id", ""))
    shape.set("style", _style(look, x, y, w, h))
    return [shape]
