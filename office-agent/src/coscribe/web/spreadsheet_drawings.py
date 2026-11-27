"""The bounded subset of worksheet drawings the read-only preview can display."""

from __future__ import annotations

import base64
import math
from contextlib import suppress
from typing import Any

from openpyxl.utils.cell import range_to_tuple

_MAX_POINTS = 80
_IMAGE_BYTES = 4 * 1024 * 1024


def _anchor(drawing: Any) -> dict[str, Any] | None:
    anchor = drawing.anchor
    start = getattr(anchor, "_from", None)
    if start is None or not (0 <= start.row < 200_000 and 0 <= start.col < 16_384):
        return None
    origin = [start.row + 1, start.col + 1, start.rowOff / 9525, start.colOff / 9525]
    end = getattr(anchor, "to", None)
    if end is not None and 0 <= end.row < 200_000 and 0 <= end.col < 16_384:
        return {
            "origin": origin,
            "end": [end.row + 1, end.col + 1, end.rowOff / 9525, end.colOff / 9525],
        }
    extent = getattr(anchor, "ext", None)
    if extent is None:
        return None
    return {"origin": origin, "size": [min(extent.cx / 9525, 6000), min(extent.cy / 9525, 6000)]}


def _series_values(source: Any, cached: Any) -> list[Any]:
    for name in ("numRef", "strRef", "numLit", "strLit"):
        data = getattr(source, name, None)
        if data is None:
            continue
        if name.endswith("Lit"):
            return _points(data)
        with suppress(KeyError, ValueError, TypeError):
            sheet, (left, top, right, bottom) = range_to_tuple(data.f)
            if left is None or top is None or right is None or bottom is None:
                return []
            width = right - left + 1
            index = range(min(width * (bottom - top + 1), _MAX_POINTS))
            rows = cached.get(sheet, {})
            values = [rows.get((top + i // width, left + i % width)) for i in index]
            if any(value is not None for value in values):
                return values
        return _points(getattr(data, "numCache", None) or getattr(data, "strCache", None))
    return []


def _points(data: Any) -> list[Any]:
    points: list[Any] = [None] * _MAX_POINTS
    last = 0
    for point in getattr(data, "pt", ()):
        if 0 <= point.idx < _MAX_POINTS:
            points[point.idx] = point.v
            last = max(last, point.idx + 1)
    return points[:last]


def chart_references(sheet: Any) -> set[str]:
    names: set[str] = set()
    for chart in sheet._charts[:24]:
        for series in chart.series[:12]:
            for source in (getattr(series, "val", None), getattr(series, "cat", None)):
                for name in ("numRef", "strRef"):
                    formula = getattr(getattr(source, name, None), "f", None)
                    if formula:
                        with suppress(ValueError):
                            names.add(range_to_tuple(formula)[0])
    return names


def _title(chart: Any) -> str:
    rich = getattr(getattr(chart.title, "tx", None), "rich", None)
    return " ".join(run.t for paragraph in getattr(rich, "p", ()) for run in paragraph.r if run.t)[
        :240
    ]


def _number(value: Any) -> float | None:
    with suppress(TypeError, ValueError, OverflowError):
        number = float(value)
        if math.isfinite(number) and abs(number) <= 1e100:
            return number
    return None


def _chart(chart: Any, cached: Any) -> dict[str, Any] | None:
    anchor = _anchor(chart)
    if anchor is None:
        return None
    kind = {"BarChart": chart.type if hasattr(chart, "type") else None, "LineChart": "line"}.get(
        type(chart).__name__
    )
    if len(chart._charts) > 1 or getattr(chart, "grouping", "") in {"stacked", "percentStacked"}:
        kind = None
    series = (
        [
            [_number(value) for value in _series_values(getattr(item, "val", None), cached)]
            for item in chart.series[:12]
        ]
        if kind
        else []
    )
    categories = (
        next(
            (
                values
                for item in chart.series[:12]
                if (values := _series_values(getattr(item, "cat", None), cached))
            ),
            [],
        )
        if kind
        else []
    )
    scaling = getattr(getattr(chart, "y_axis", None), "scaling", None)
    return {
        **anchor,
        "kind": "chart",
        "min": _number(getattr(scaling, "min", None)),
        "max": _number(getattr(scaling, "max", None)),
        "plot": kind,
        "title": _title(chart),
        "series": series,
        "labels": [str(value)[:64] if value is not None else "" for value in categories],
    }


def drawings(sheet: Any, cached: Any) -> list[dict[str, Any]]:
    result = [item for chart in sheet._charts[:24] if (item := _chart(chart, cached)) is not None]
    image_bytes = 0
    for image in sheet._images[:24]:
        anchor = _anchor(image)
        mime = {"png": "png", "gif": "gif", "jpeg": "jpeg", "jpg": "jpeg"}.get(image.format)
        if anchor is None or mime is None:
            continue
        content = image._data()
        if image_bytes + len(content) <= _IMAGE_BYTES:
            image_bytes += len(content)
            src = f"data:image/{mime};base64,{base64.b64encode(content).decode('ascii')}"
            result.append({**anchor, "kind": "image", "src": src})
    return result
