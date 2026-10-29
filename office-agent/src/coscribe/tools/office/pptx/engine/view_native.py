"""A deck's native charts and tables drawn as SVG, for the Slides panel (decision 0016).

A page holds a chart or table as JSON only; PowerPoint draws it from the compiled slide. The panel
shows the page as an image, so it draws them here from what the build wrote (the table's cells,
the chart's cached values, colours and fonts), in the page's own px. Chart types this does not
draw stay a labelled box; the .pptx is the authority either way.
"""

from __future__ import annotations

import math
import re
from collections.abc import Collection, Iterator
from dataclasses import dataclass
from typing import Any
from xml.sax.saxutils import escape

from lxml import etree

from ...._native_svg.svg_to_pptx.drawingml.utils import estimate_text_cluster_widths

_A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
_C = "{http://schemas.openxmlformats.org/drawingml/2006/chart}"
_P = "{http://schemas.openxmlformats.org/presentationml/2006/main}"
_R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
_CHART_URI = "http://schemas.openxmlformats.org/drawingml/2006/chart"
_TABLE_URI = "http://schemas.openxmlformats.org/drawingml/2006/table"
_EMU_PER_PT = 12700
# PowerPoint's defaults where the XML says nothing.
_CELL_MARGIN_X, _CELL_MARGIN_Y = 91440, 45720
_CHART_TEXT = "595959"
_CHART_SIZE_PT = 10.0
_LINE_HEIGHT = 1.2
_DRAWN = {"barChart", "lineChart", "areaChart", "pieChart", "doughnutChart"}


@dataclass
class _Series:
    name: str
    colour: str
    values: list[float | None]
    points: dict[int, str]


def native_drawings(
    slide: Any, emu_per_px: float, font: str, skip: Collection[Any] = ()
) -> list[str]:
    """The SVG markup of each chart and table on the python-pptx `slide`, in document order,
    placed in page px, but for those inside the shapes in `skip`. `font` is the page's
    font-family, for text the XML leaves to the theme."""
    drawings = []
    for frame in slide.shapes._spTree.iter(f"{_P}graphicFrame"):
        if any(node is shape for node in frame.iterancestors() for shape in skip) or any(
            frame is shape for shape in skip
        ):
            continue
        data = frame.find(f"{_A}graphic/{_A}graphicData")
        if data is None:
            continue
        box = _box(frame, emu_per_px)
        if data.get("uri") == _TABLE_URI:
            drawings.append(_table(data.find(f"{_A}tbl"), box, emu_per_px, font))
        elif data.get("uri") == _CHART_URI:
            ref = data.find(f"{_C}chart")
            part = slide.part.related_part(ref.get(f"{_R}id")) if ref is not None else None
            space = etree.fromstring(part.blob) if part is not None else None
            drawings.append(_chart(space, box, font, emu_per_px) if space is not None else "")
    return drawings


def _box(frame: Any, emu_per_px: float) -> tuple[float, float, float, float]:
    off, ext = frame.find(f"{_P}xfrm/{_A}off"), frame.find(f"{_P}xfrm/{_A}ext")
    return (
        int(off.get("x")) / emu_per_px,
        int(off.get("y")) / emu_per_px,
        int(ext.get("cx")) / emu_per_px,
        int(ext.get("cy")) / emu_per_px,
    )


# Tables


def _table(tbl: Any, box: tuple[float, float, float, float], emu: float, font: str) -> str:
    if tbl is None:
        return ""
    x0, y0 = box[0], box[1]
    widths = [int(c.get("w")) / emu for c in tbl.iter(f"{_A}gridCol")]
    lefts = [x0 + sum(widths[:i]) for i in range(len(widths) + 1)]
    rows = tbl.findall(f"{_A}tr")
    cells = [r.findall(f"{_A}tc") for r in rows]
    heights = [int(r.get("h", 0)) / emu for r in rows]
    # A row grows to hold its text, as in PowerPoint.
    for i, row in enumerate(cells):
        for j, tc in enumerate(row):
            if _covered(tc) or int(tc.get("rowSpan", 1)) > 1:
                continue
            width = _span(lefts, j, int(tc.get("gridSpan", 1)))
            needed = _cell_lines(tc, width, emu, font)[1] + 2 * _CELL_MARGIN_Y / emu
            heights[i] = max(heights[i], needed)
    tops = [y0 + sum(heights[:i]) for i in range(len(heights) + 1)]
    fills: list[str] = []
    lines: list[str] = []
    texts: list[str] = []
    for i, row in enumerate(cells):
        for j, tc in enumerate(row):
            if _covered(tc):
                continue
            x, y = lefts[j], tops[i]
            w = _span(lefts, j, int(tc.get("gridSpan", 1)))
            h = tops[min(i + int(tc.get("rowSpan", 1)), len(rows))] - y
            pr = tc.find(f"{_A}tcPr")
            fill = _solid(pr) if pr is not None else None
            if fill:
                fills.append(_rect(x, y, w, h, fill))
            lines.extend(_borders(pr, x, y, w, h, emu))
            texts.append(_cell_text(tc, x, y, w, h, emu, font))
    return f'<g data-native="table">{"".join(fills + lines + texts)}</g>'


def _covered(tc: Any) -> bool:
    return bool(tc.get("hMerge") == "1" or tc.get("vMerge") == "1")


def _span(lefts: list[float], start: int, count: int) -> float:
    return lefts[min(start + count, len(lefts) - 1)] - lefts[start]


def _borders(pr: Any, x: float, y: float, w: float, h: float, emu: float) -> Iterator[str]:
    if pr is None:
        return
    ends = {
        "lnL": (x, y, x, y + h),
        "lnR": (x + w, y, x + w, y + h),
        "lnT": (x, y, x + w, y),
        "lnB": (x, y + h, x + w, y + h),
    }
    for tag, (a, b, c, d) in ends.items():
        line = pr.find(f"{_A}{tag}")
        colour = _solid(line) if line is not None else None
        if colour:
            width = int(line.get("w", 12700)) / emu
            yield (
                f'<line x1="{a:.2f}" y1="{b:.2f}" x2="{c:.2f}" y2="{d:.2f}" '
                f'stroke="#{colour}" stroke-width="{width:.2f}"/>'
            )


def _cell_lines(tc: Any, width: float, emu: float, font: str) -> tuple[list[Any], float]:
    """The cell's lines as (paragraph alignment, [(text, run style)], size px), and their height."""
    inner = max(width - 2 * _CELL_MARGIN_X / emu, 1.0)
    lines: list[Any] = []
    for p in tc.iter(f"{_A}p"):
        ppr = p.find(f"{_A}pPr")
        align = ppr.get("algn", "l") if ppr is not None else "l"
        runs = [(r.findtext(f"{_A}t") or "", _run_style(r, font, emu)) for r in p.iter(f"{_A}r")]
        size = max((s["size"] for _t, s in runs), default=18 * _EMU_PER_PT / emu)
        lines.extend((align, line, size) for line in _wrap(runs, inner))
    return lines, sum(size * _LINE_HEIGHT for _a, _l, size in lines)


def _cell_text(tc: Any, x: float, y: float, w: float, h: float, emu: float, font: str) -> str:
    lines, height = _cell_lines(tc, w, emu, font)
    pr = tc.find(f"{_A}tcPr")
    anchor = pr.get("anchor", "t") if pr is not None else "t"
    top = y + _CELL_MARGIN_Y / emu
    if anchor == "ctr":
        top = y + (h - height) / 2
    elif anchor == "b":
        top = y + h - _CELL_MARGIN_Y / emu - height
    out = []
    for align, runs, size in lines:
        top += size * _LINE_HEIGHT
        out.append(_text_line(runs, align, x, w, top - size * 0.25 * _LINE_HEIGHT, emu))
    return "".join(out)


def _text_line(runs: list[Any], align: str, x: float, w: float, baseline: float, emu: float) -> str:
    margin = _CELL_MARGIN_X / emu
    anchor, at = {"ctr": ("middle", x + w / 2), "r": ("end", x + w - margin)}.get(
        align, ("start", x + margin)
    )
    spans = "".join(
        f'<tspan font-family="{escape(s["family"])}" font-size="{s["size"]:.2f}" '
        f'font-weight="{s["weight"]}" font-style="{s["style"]}" fill="#{s["colour"]}">'
        f"{escape(text)}</tspan>"
        for text, s in runs
    )
    return f'<text x="{at:.2f}" y="{baseline:.2f}" text-anchor="{anchor}">{spans}</text>'


def _run_style(run: Any, font: str, emu: float) -> dict[str, Any]:
    rpr = run.find(f"{_A}rPr")
    get = rpr.get if rpr is not None else (lambda _k, d=None: d)
    face = None
    if rpr is not None:
        for tag in ("ea", "latin"):
            el = rpr.find(f"{_A}{tag}")
            if el is not None and not el.get("typeface", "+").startswith("+"):
                face = el.get("typeface")
                break
    return {
        "size": int(get("sz", 1800)) / 100 * _EMU_PER_PT / emu,
        "weight": "bold" if get("b") == "1" else "normal",
        "style": "italic" if get("i") == "1" else "normal",
        "colour": (_solid(rpr) if rpr is not None else None) or "000000",
        "family": face or font,
    }


def _wrap(runs: list[tuple[str, dict[str, Any]]], width: float) -> list[list[Any]]:
    """Runs broken into lines that fit `width`: between CJK characters or at spaces."""
    lines: list[list[Any]] = [[]]
    used = 0.0
    for text, style in runs:
        for piece in _pieces(text):
            advance = _width(piece, style)
            if used and used + advance > width and piece.strip():
                lines.append([])
                used = 0.0
                piece = piece.lstrip()
                advance = _width(piece, style)
            line = lines[-1]
            if line and line[-1][1] is style:
                line[-1] = (line[-1][0] + piece, style)
            else:
                line.append((piece, style))
            used += advance
    return [line for line in lines if line] or [[]]


def _pieces(text: str) -> Iterator[str]:
    word = ""
    for ch in text:
        if ord(ch) > 0x2E7F:
            if word:
                yield word
            word = ""
            yield ch
        elif ch == " ":
            yield word + ch
            word = ""
        else:
            word += ch
    if word:
        yield word


def _width(text: str, style: dict[str, Any]) -> float:
    weight = "700" if style["weight"] == "bold" else "400"
    widths = estimate_text_cluster_widths(text, style["size"], weight, font_family=style["family"])
    return float(sum(widths))


# Charts


def _chart(space: Any, box: tuple[float, float, float, float], font: str, emu: float) -> str:
    x, y, w, h = box
    plot = space.find(f"{_C}chart/{_C}plotArea")
    kinds = [etree.QName(el).localname for el in plot] if plot is not None else []
    kind = next((k for k in kinds if k.endswith("Chart")), None)
    size = _text_size(space, emu)
    colour = _text_colour(space)
    out: list[str] = []
    title = _title(space)
    if title:
        out.append(_label(x + w / 2, y + size * 1.6, title, size * 1.3, colour, font, "middle"))
        y, h = y + size * 2.2, h - size * 2.2
    if kind not in _DRAWN:
        out.append(_rect(x, y, w, h, "F1F5F9"))
        name = (kind or "chart").removesuffix("Chart")
        out.append(_label(x + w / 2, y + h / 2, f"{name} chart", size, colour, font, "middle"))
        return f'<g data-native="chart">{"".join(out)}</g>'
    group = plot.find(f"{_C}{kind}")
    series, categories = _series(group, kind)
    legend = space.find(f"{_C}chart/{_C}legend")
    if legend is not None and series:
        names = (
            [(c, series[0].points.get(i, _palette(i))) for i, c in enumerate(categories)]
            if kind in {"pieChart", "doughnutChart"}
            else [(s.name, s.colour) for s in series]
        )
        out.append(_legend(names, x, y + h - size * 1.6, w, size, colour, font))
        h -= size * 2.4
    if kind in {"pieChart", "doughnutChart"}:
        hole = group.find(f"{_C}holeSize")
        ratio = (
            int(hole.get("val", 50)) / 100 if kind == "doughnutChart" and hole is not None else 0
        )
        out.append(_pie(series, (x, y, w, h), ratio))
    else:
        out.append(_axes_chart(group, kind, series, categories, (x, y, w, h), size, colour, font))
    return f'<g data-native="chart">{"".join(out)}</g>'


def _series(group: Any, kind: str) -> tuple[list[_Series], list[str]]:
    series: list[_Series] = []
    categories: list[str] = []
    for i, ser in enumerate(group.findall(f"{_C}ser")):
        name = "".join(t.text or "" for t in ser.iterfind(f"{_C}tx//{_C}v"))
        sppr = ser.find(f"{_C}spPr")
        colour = None
        if sppr is not None:
            colour = _solid(sppr) if kind != "lineChart" else _solid(sppr.find(f"{_A}ln"))
        points = {}
        for dpt in ser.findall(f"{_C}dPt"):
            fill = _solid(dpt.find(f"{_C}spPr"))
            if fill:
                points[int(dpt.find(f"{_C}idx").get("val"))] = fill
        cat = _cache(ser.find(f"{_C}cat"))
        categories = categories or [str(v) for v in cat]
        values = [_number(v) for v in _cache(ser.find(f"{_C}val"))]
        series.append(_Series(name, colour or _palette(i), values, points))
    return series, categories


def _cache(ref: Any) -> list[str]:
    if ref is None:
        return []
    pts = list(ref.iter(f"{_C}pt"))
    count = ref.find(f".//{_C}ptCount")
    values = [""] * (int(count.get("val")) if count is not None else len(pts))
    for pt in pts:
        index = int(pt.get("idx", 0))
        if index < len(values):
            values[index] = pt.findtext(f"{_C}v") or ""
    return values


def _number(value: str) -> float | None:
    try:
        return float(value)
    except ValueError:
        return None


def _axes_chart(
    group: Any,
    kind: str,
    series: list[_Series],
    categories: list[str],
    box: tuple[float, float, float, float],
    size: float,
    colour: str,
    font: str,
) -> str:
    x, y, w, h = box
    grouping = _val(group, "grouping") or "clustered"
    horizontal = _val(group, "barDir") == "bar"
    count = max([len(categories)] + [len(s.values) for s in series])
    totals = [
        sum(max(s.values[i] or 0, 0) for s in series if i < len(s.values)) for i in range(count)
    ]
    stacked = grouping in {"stacked", "percentStacked"}
    if grouping == "percentStacked":
        low, high = 0.0, 100.0
    else:
        values = [v for s in series for v in s.values if v is not None]
        peak = max(totals) if stacked else max(values, default=0.0)
        low, high = min(min(values, default=0.0), 0.0), max(peak, 0.0)
    plot = group.getparent()
    ticks, low, high = _scale(plot, low, high)
    number_format = _number_format(plot)
    labels = [_tick_label(t, grouping == "percentStacked", number_format) for t in ticks]
    label_room = max((_width(t, _plain(size, font)) for t in labels), default=0) + size * 0.6
    out = []
    if horizontal:
        cat_room = max((_width(c, _plain(size, font)) for c in categories), default=0) + size
        left, top, right, bottom = x + cat_room, y + size * 0.6, x + w - size, y + h - size * 1.8
    else:
        left, top, right, bottom = (
            x + label_room,
            y + size * 0.6,
            x + w - size * 0.6,
            y + h - size * 2,
        )
    category_title, value_title = _axis_title(plot, "catAx"), _axis_title(plot, "valAx")
    bottom_title, left_title = (
        (value_title, category_title) if horizontal else (category_title, value_title)
    )
    if left_title:
        left += size * 1.8
    if bottom_title:
        bottom -= size * 1.8
    span = high - low or 1.0

    def at(value: float) -> float:
        share = (value - low) / span
        return left + share * (right - left) if horizontal else bottom - share * (bottom - top)

    for tick, label in zip(ticks, labels, strict=True):
        p = at(tick)
        if horizontal:
            out.append(_line(p, top, p, bottom, "D9D9D9"))
            out.append(_label(p, bottom + size * 1.3, label, size, colour, font, "middle"))
        else:
            out.append(_line(left, p, right, p, "D9D9D9"))
            out.append(_label(left - size * 0.4, p + size * 0.35, label, size, colour, font, "end"))
    band = ((bottom - top) if horizontal else (right - left)) / max(count, 1)
    for i, name in enumerate(categories):
        middle = (top if horizontal else left) + band * (i + 0.5)
        if horizontal:
            out.append(
                _label(left - size * 0.4, middle + size * 0.35, name, size, colour, font, "end")
            )
        else:
            out.append(_label(middle, bottom + size * 1.4, name, size, colour, font, "middle"))
    if kind == "barChart":
        out.extend(
            _bars(series, totals, grouping, band, horizontal, at, (left, top, right, bottom))
        )
    else:
        out.extend(_lines(series, kind, totals, grouping, band, at, (left, top, bottom)))
    zero = at(0.0)
    out.append(
        _line(zero, top, zero, bottom, "BFBFBF")
        if horizontal
        else _line(left, zero, right, zero, "BFBFBF")
    )
    if bottom_title:
        middle = (left + right) / 2
        out.append(_label(middle, y + h - size * 0.25, bottom_title, size, colour, font, "middle"))
    if left_title:
        cx, cy = x + size * 0.8, (top + bottom) / 2
        turned = _label(cx, cy, left_title, size, colour, font, "middle")
        out.append(f'<g transform="rotate(-90 {cx:.2f} {cy:.2f})">{turned}</g>')
    return "".join(out)


def _bars(
    series: list[_Series],
    totals: list[float],
    grouping: str,
    band: float,
    horizontal: bool,
    at: Any,
    frame: tuple[float, float, float, float],
) -> Iterator[str]:
    left, top, _right, _bottom = frame
    stacked = grouping in {"stacked", "percentStacked"}
    slots = 1 if stacked else len(series)
    thick = band / (slots + 1.5)  # PowerPoint's default gap is 150% of a bar
    base = [0.0] * len(totals)
    for k, s in enumerate(series):
        for i, value in enumerate(s.values):
            if value is None:
                continue
            if grouping == "percentStacked":
                value = value / totals[i] * 100 if totals[i] else 0.0
            start = base[i] if stacked else 0.0
            end = start + value
            if stacked:
                base[i] = end
            offset = band * i + band * 0.75 / (slots + 1.5) * 1 + thick * (0 if stacked else k)
            a, b = sorted((at(start), at(end)))
            fill = s.points.get(i, s.colour)
            if horizontal:
                yield _rect(a, top + offset, b - a, thick, fill)
            else:
                yield _rect(left + offset, a, thick, b - a, fill)


def _lines(
    series: list[_Series],
    kind: str,
    totals: list[float],
    grouping: str,
    band: float,
    at: Any,
    frame: tuple[float, float, float],
) -> Iterator[str]:
    left, _top, bottom = frame
    base = [0.0] * len(totals)
    for s in series:
        points = []
        for i, value in enumerate(s.values):
            if value is None:
                continue
            if grouping == "percentStacked":
                value = value / totals[i] * 100 if totals[i] else 0.0
            if grouping in {"stacked", "percentStacked"}:
                base[i] += value
                value = base[i]
            points.append((left + band * (i + 0.5), at(value)))
        if not points:
            continue
        path = " ".join(f"{px:.2f},{py:.2f}" for px, py in points)
        if kind == "areaChart":
            first, last = points[0][0], points[-1][0]
            yield (
                f'<polygon points="{first:.2f},{bottom:.2f} {path} {last:.2f},{bottom:.2f}" '
                f'fill="#{s.colour}" fill-opacity="0.85"/>'
            )
        else:
            yield f'<polyline points="{path}" fill="none" stroke="#{s.colour}" stroke-width="2.5"/>'


def _pie(series: list[_Series], box: tuple[float, float, float, float], hole: float) -> str:
    if not series:
        return ""
    x, y, w, h = box
    r = max(min(w, h) / 2 - 4, 1.0)
    cx, cy = x + w / 2, y + h / 2
    values = [max(v or 0, 0) for v in series[0].values]
    total = sum(values) or 1.0
    angle, out = -math.pi / 2, []
    for i, value in enumerate(values):
        sweep = value / total * 2 * math.pi
        if sweep <= 0:
            continue
        fill = series[0].points.get(i, _palette(i))
        # A full turn has no arc to draw, so it stops just short of one.
        end = angle + min(sweep, 2 * math.pi - 1e-4)
        large = 1 if sweep > math.pi else 0
        outer = _arc(cx, cy, r, angle, end, large, 1)
        inner = (
            _arc(cx, cy, r * hole, end, angle, large, 0, line=True)
            if hole
            else f" L{cx:.2f},{cy:.2f}"
        )
        out.append(f'<path d="{outer}{inner} Z" fill="#{fill}" stroke="#FFFFFF" stroke-width="1"/>')
        angle += sweep
    return "".join(out)


def _arc(
    cx: float,
    cy: float,
    r: float,
    start: float,
    end: float,
    large: int,
    sweep: int,
    line: bool = False,
) -> str:
    x1, y1 = cx + r * math.cos(start), cy + r * math.sin(start)
    x2, y2 = cx + r * math.cos(end), cy + r * math.sin(end)
    move = "L" if line else "M"
    return f"{move}{x1:.2f},{y1:.2f} A{r:.2f},{r:.2f} 0 {large} {sweep} {x2:.2f},{y2:.2f}"


def _legend(
    names: list[tuple[str, str]], x: float, y: float, w: float, size: float, colour: str, font: str
) -> str:
    items = [(n, c, _width(n, _plain(size, font)) + size * 2) for n, c in names]
    total = sum(width for _n, _c, width in items)
    at = x + max((w - total) / 2, 0)
    out = []
    for name, fill, width in items:
        out.append(_rect(at, y - size * 0.7, size * 0.7, size * 0.7, fill))
        out.append(_label(at + size, y, name, size, colour, font, "start"))
        at += width
    return "".join(out)


def _ticks(low: float, high: float) -> list[float]:
    """Axis ticks as PowerPoint picks them: steps of 1, 2 or 5 times a power of ten, about five."""
    if high <= low:
        high = low + 1
    raw = (high - low) / 5
    power = 10 ** math.floor(math.log10(raw))
    step = next(m * power for m in (1, 2, 5, 10) if m * power >= raw)
    start = math.floor(low / step) * step
    ticks = [start]
    while ticks[-1] < high - 1e-9:
        ticks.append(ticks[-1] + step)
    return ticks


def _fixed_range(plot: Any) -> tuple[float | None, float | None]:
    """The value axis's own minimum and maximum, when the chart sets them."""
    scaling = plot.find(f"{_C}valAx/{_C}scaling")
    if scaling is None:
        return None, None
    return _number(_val(scaling, "min") or ""), _number(_val(scaling, "max") or "")


def _scale(plot: Any, low: float, high: float) -> tuple[list[float], float, float]:
    """The ticks and the ends of the value axis: the chart's own minimum and maximum, else as
    PowerPoint rounds them."""
    fixed_low, fixed_high = _fixed_range(plot)
    ticks = _ticks(
        low if fixed_low is None else fixed_low, high if fixed_high is None else fixed_high
    )
    if fixed_low is not None:
        ticks = [t for t in ticks if t >= fixed_low - 1e-9]
    if fixed_high is not None:
        ticks = [t for t in ticks if t <= fixed_high + 1e-9]
    ticks = ticks or [low, high]
    return (
        ticks,
        ticks[0] if fixed_low is None else fixed_low,
        ticks[-1] if fixed_high is None else fixed_high,
    )


def _number_format(plot: Any) -> str | None:
    fmt = plot.find(f"{_C}valAx/{_C}numFmt")
    return fmt.get("formatCode") if fmt is not None else None


def _axis_title(plot: Any, axis: str) -> str:
    title = plot.find(f"{_C}{axis}/{_C}title")
    return "".join(t.text or "" for t in title.iter(f"{_A}t")) if title is not None else ""


_FORMAT = re.compile(r"([^0#]*)([#,]*0(?:\.(0+))?)(%?)([^0#]*)")


def _formatted(value: float, fmt: str) -> str | None:
    """A number in the simple Excel formats the panel offers ("#,##0", "0.0", "0%", "$#,##0")."""
    match = _FORMAT.fullmatch(fmt.split(";")[0])
    if match is None:
        return None
    prefix, number, decimals, percent, suffix = match.groups()
    shown = value * 100 if percent else value
    digits = len(decimals or "")
    text = f"{shown:,.{digits}f}" if "," in number else f"{shown:.{digits}f}"
    return f"{prefix}{text}{percent}{suffix}".replace('"', "")


def _tick_label(value: float, percent: bool, fmt: str | None = None) -> str:
    if fmt and fmt != "General" and (formatted := _formatted(value, fmt)) is not None:
        return formatted
    text = f"{value:,.0f}" if abs(value) >= 1 or value == 0 else f"{value:g}"
    return f"{text}%" if percent else text


def _title(space: Any) -> str:
    title = space.find(f"{_C}chart/{_C}title")
    if title is None:
        return ""
    return "".join(t.text or "" for t in title.iter(f"{_A}t"))


def _text_size(space: Any, emu: float) -> float:
    defrpr = space.find(f".//{_C}txPr//{_A}defRPr[@sz]")
    pt = int(defrpr.get("sz")) / 100 if defrpr is not None else _CHART_SIZE_PT
    return pt * _EMU_PER_PT / emu


def _text_colour(space: Any) -> str:
    defrpr = space.find(f".//{_C}txPr//{_A}defRPr")
    return (_solid(defrpr) if defrpr is not None else None) or _CHART_TEXT


def _val(group: Any, tag: str) -> str | None:
    el = group.find(f"{_C}{tag}")
    return el.get("val") if el is not None else None


def _palette(index: int) -> str:
    from ...._native_svg.svg_to_pptx.native_objects.chart_data import _DEFAULT_CHART_COLORS

    return str(_DEFAULT_CHART_COLORS[index % len(_DEFAULT_CHART_COLORS)])


# Shared


def _solid(parent: Any) -> str | None:
    if parent is None:
        return None
    fill = parent.find(f"{_A}solidFill/{_A}srgbClr")
    return fill.get("val") if fill is not None else None


def _plain(size: float, font: str) -> dict[str, Any]:
    return {"size": size, "weight": "normal", "family": font}


def _rect(x: float, y: float, w: float, h: float, fill: str) -> str:
    size = f'width="{max(w, 0):.2f}" height="{max(h, 0):.2f}"'
    return f'<rect x="{x:.2f}" y="{y:.2f}" {size} fill="#{fill}"/>'


def _line(x1: float, y1: float, x2: float, y2: float, colour: str) -> str:
    ends = f'x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}"'
    return f'<line {ends} stroke="#{colour}" stroke-width="1"/>'


def _label(x: float, y: float, text: str, size: float, colour: str, font: str, anchor: str) -> str:
    return (
        f'<text x="{x:.2f}" y="{y:.2f}" font-family="{escape(font)}" font-size="{size:.2f}" '
        f'fill="#{colour}" text-anchor="{anchor}">{escape(text)}</text>'
    )
