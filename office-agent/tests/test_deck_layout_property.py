"""Property test for the container layout (decision 0018): any tree of `<x-stack>` containers, in
rows and columns up to three levels deep with random gap, padding, align, justify and children
that are fixed, growing, shrinking or sized by their content, is laid out so that

- every child lies inside its container, unless it is sized by its content and larger than the
  room (the engine lets it overflow rather than squeeze its text);
- siblings follow one another along the main axis, a gap apart;
- growing children share out all the free room in proportion to their `flex-grow`;
- the room left over is placed by `justify`;
- laying the same tree out twice gives the same boxes.

The tree is built as data first and written to a section after, so the checks read what the
generator meant, not what the engine made of it.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest
from hypothesis import HealthCheck, given, reject, settings
from hypothesis import strategies as st

from coscribe.tools.office.pptx.engine.section_format import SectionError, parse_section

_SETTINGS = settings(
    deadline=None,
    derandomize=True,
    max_examples=300,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.data_too_large],
)
# The section reader rounds a leaf's box to 0.01px.
EPS = 0.05
_GROWS = [0.5, 1.0, 1.5, 2.0, 3.0]
_SHRINKS = [0.5, 1.0, 2.0, 3.0]
_WORDS = ["Books", "A short line of text.", "Every book gets a folder of its own. " * 3]

Box = tuple[float, float, float, float]
Path = tuple[int, ...]


@dataclass
class Item:
    """One child of a container, as the generator meant it."""

    kind: str  # "shape", "text" or "stack"
    main: float | None = None  # width in a row, height in a column
    cross: float | None = None
    grow: float = 0.0
    shrink: float = 1.0
    words: str = ""
    # A container's own settings and children.
    row: bool = False
    gap: float = 0.0
    pad: float = 0.0
    align: str = "stretch"
    justify: str = "start"
    kids: list[Item] = field(default_factory=list)

    @property
    def hug_main(self) -> bool:
        """Sized by its content along its parent's main axis: it never shrinks below it."""
        return self.main is None and self.grow == 0


def _write(item: Item, parent_row: bool, at: Box | None = None) -> str:
    """The section text for `item`, a child of a container laid out as a row or a column; the
    section's own container is placed at `at`."""
    if at is not None:
        style = [f"left:{at[0]:g}px", f"top:{at[1]:g}px", f"width:{at[2]:g}px"]
        style.append(f"height:{at[3]:g}px")
    else:
        main, cross = ("width", "height") if parent_row else ("height", "width")
        style = []
        if item.main is not None:
            style.append(f"{main}:{item.main:g}px")
        if item.cross is not None:
            style.append(f"{cross}:{item.cross:g}px")
        if item.grow:
            style.append(f"flex-grow:{item.grow:g}")
        if item.shrink != 1.0:
            style.append(f"flex-shrink:{item.shrink:g}")
    if item.kind == "text":
        return f'<p style="{";".join(style)}">{item.words}</p>'
    if item.kind == "shape":
        return f'<x-shape style="{";".join([*style, "background:#111111"])}"/>'
    style += [f"gap:{item.gap:g}px", f"padding:{item.pad:g}px", f"align:{item.align}"]
    style += [f"justify:{item.justify}", "background:#EEEEEE"]
    inner = "".join(_write(k, item.row) for k in item.kids)
    layout = "row" if item.row else "column"
    return f'<x-stack data-layout="{layout}" style="{";".join(style)}">{inner}</x-stack>'


@st.composite
def _stack(draw: st.DrawFn, depth: int, width: float | None, height: float | None) -> Item:
    """A container (`depth` levels down) with its children; `width` and `height` are its size
    when it is known, None when its parent decides."""
    row = draw(st.booleans())
    item = Item(
        kind="stack",
        row=row,
        gap=float(draw(st.integers(0, 24))),
        pad=float(draw(st.integers(0, 24))),
        align=draw(st.sampled_from(["start", "center", "end", "stretch"])),
        justify=draw(st.sampled_from(["start", "center", "end", "between"])),
    )
    inner_w = None if width is None else width - 2 * item.pad
    inner_h = None if height is None else height - 2 * item.pad
    main_room, cross_room = (inner_w, inner_h) if row else (inner_h, inner_w)
    for _ in range(draw(st.integers(1, 4 if depth == 0 else 3))):
        item.kids.append(draw(_child(depth, item, main_room, cross_room)))
    return item


def _size(draw: st.DrawFn, room: float | None, low: int, high: int) -> float:
    if room is None or room < low:
        return float(draw(st.integers(low, high)))
    return float(draw(st.integers(low, min(high, int(room)))))


@st.composite
def _child(
    draw: st.DrawFn, depth: int, parent: Item, main_room: float | None, cross_room: float | None
) -> Item:
    kind = draw(st.sampled_from(["shape", "text", "stack"] if depth < 2 else ["shape", "text"]))
    # A row needs a width or flex-grow of each child, a shape its size along a column too.
    sizing = draw(st.sampled_from(["fixed", "grow", "both", "hug"]))
    if sizing == "hug" and (parent.row or kind == "shape"):
        sizing = "fixed"
    if kind == "stack":
        item = draw(_stack(depth + 1, None, None))
    else:
        item = Item(kind=kind, words=draw(st.sampled_from(_WORDS)) if kind == "text" else "")
    if sizing in ("fixed", "both"):
        item.main = _size(draw, main_room, 40, 260)
    if sizing in ("grow", "both"):
        item.grow = draw(st.sampled_from(_GROWS))
    item.shrink = draw(st.sampled_from([1.0, 1.0, *_SHRINKS]))
    # Across the container a shape has a size of its own unless it is stretched to the room.
    stretched = parent.align == "stretch" and cross_room is not None
    if (kind == "shape" and not stretched) or draw(st.booleans()):
        item.cross = _size(draw, cross_room, 20, 200)
    return item


@st.composite
def _section(draw: st.DrawFn) -> tuple[Item, Box]:
    width = float(draw(st.integers(500, 1700)))
    height = float(draw(st.integers(300, 900)))
    at = (float(draw(st.integers(0, 200))), float(draw(st.integers(0, 100))), width, height)
    return draw(_stack(0, width, height)), at


def _lay_out(root: Item, at: Box) -> dict[Path, Box]:
    try:
        section = parse_section(f"<section>{_write(root, False, at)}</section>")
    except SectionError as e:
        if "must be positive" in str(e):  # a child squeezed to nothing: no layout to check
            reject()
        raise
    if any(n.box is None for n in section.nodes):  # a child squeezed to nothing has no box
        reject()
    return {n.path: n.box for n in section.nodes}


def _check_container(item: Item, path: Path, boxes: dict[Path, Box]) -> None:
    x, y, w, h = boxes[path]
    inner = (x + item.pad, y + item.pad, w - 2 * item.pad, h - 2 * item.pad)
    # (start, size) along the container's main axis, then across it.
    main0, room = (inner[0], inner[2]) if item.row else (inner[1], inner[3])
    cross0, across = (inner[1], inner[3]) if item.row else (inner[0], inner[2])
    spans = []
    for j in range(len(item.kids)):
        kx, ky, kw, kh = boxes[(*path, j)]
        spans.append(((kx, kw), (ky, kh)) if item.row else ((ky, kh), (kx, kw)))
    gaps = item.gap * (len(spans) - 1)
    used = sum(main[1] for main, _ in spans) + gaps
    # Only what is sized by its content can push the others out of the container.
    hug = sum(main[1] for (main, _), k in zip(spans, item.kids, strict=True) if k.hug_main)
    # A shrink factor above the others can take more than a child has: the engine stops that
    # child at nothing and does not share the rest out again, so the others stay too large.
    squeezed = any(
        k.main is not None and main[1] < EPS for (main, _), k in zip(spans, item.kids, strict=True)
    )
    overflows = hug + gaps > room + EPS or squeezed

    for j, (main, cross) in enumerate(spans):
        if not overflows:
            assert main[0] >= main0 - EPS and main[0] + main[1] <= main0 + room + EPS, (j, main)
        if cross[1] <= across + EPS:
            assert cross[0] >= cross0 - EPS and cross[0] + cross[1] <= cross0 + across + EPS, (
                j,
                cross,
            )
        if j:
            before = spans[j - 1][0]
            assert main[0] >= before[0] + before[1] + item.gap - EPS, (j, before, main)

    leftover = room - used
    if leftover > EPS:
        # Nothing grew into the free room, so `justify` places it.
        first, last = spans[0][0], spans[-1][0]
        if item.justify == "between" and len(spans) > 1:
            assert first[0] == pytest.approx(main0, abs=EPS)
            assert last[0] + last[1] == pytest.approx(main0 + room, abs=EPS * len(spans))
        else:
            start = {"start": 0.0, "center": leftover / 2, "end": leftover, "between": 0.0}
            assert first[0] - main0 == pytest.approx(start[item.justify], abs=EPS), item.justify

    growing = [(main[1], k) for (main, _), k in zip(spans, item.kids, strict=True) if k.grow]
    if growing:
        # What the children ask for before the room is shared out.
        asked = gaps + sum(k.main or 0.0 for _, k in growing)
        asked += sum(main[1] for (main, _), k in zip(spans, item.kids, strict=True) if not k.grow)
        if room - asked > EPS:
            assert used == pytest.approx(room, abs=EPS * len(spans))
            shares = [(size - (k.main or 0.0)) / k.grow for size, k in growing]
            assert max(shares) - min(shares) <= EPS * len(spans) / min(_GROWS), shares

    for j, kid in enumerate(item.kids):
        if kid.kind == "stack":
            _check_container(kid, (*path, j), boxes)


@_SETTINGS
@given(_section())
def test_children_stay_in_their_container_a_gap_apart_and_share_the_room(
    tree: tuple[Item, Box],
) -> None:
    root, at = tree
    boxes = _lay_out(root, at)
    assert boxes[(0,)] == pytest.approx(at)
    _check_container(root, (0,), boxes)


@_SETTINGS
@given(_section())
def test_the_layout_is_deterministic(tree: tuple[Item, Box]) -> None:
    root, at = tree
    assert _lay_out(root, at) == _lay_out(root, at)
