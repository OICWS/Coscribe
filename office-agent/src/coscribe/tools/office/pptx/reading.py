"""A slide as text for the model: its title, text, tables, chart data and the pictures on it."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

_EMU_PER_PX = 9525


def render_slide(slide: Any, with_heading: bool = False) -> str:
    title_shape = slide.shapes.title
    title = title_shape.text if title_shape is not None else ""
    title_shape_id = title_shape.shape_id if title_shape is not None else None
    lines = [f"## {title}"] if with_heading else []
    for shape in leaf_shapes(slide.shapes):
        if title_shape_id is not None and shape.shape_id == title_shape_id:
            continue
        if shape.has_table:
            for row in shape.table.rows:
                lines.append("| " + " | ".join(cell.text for cell in row.cells) + " |")
        elif getattr(shape, "has_chart", False) and shape.has_chart:
            lines.extend(_chart_lines(shape))
        elif _is_picture(shape):
            # A redesign that only sees text drops the pictures without knowing they were there.
            width, height = (round(v / _EMU_PER_PX) for v in (shape.width, shape.height))
            lines.append(f"[picture {shape.name!r}, {shape.image.ext}, {width}x{height} px]")
        elif shape.has_text_frame:
            for paragraph in shape.text_frame.paragraphs:
                if paragraph.text:
                    lines.append(f"- {paragraph.text}")
    return "\n".join(lines)


def leaf_shapes(shapes: Any) -> Iterator[Any]:
    """Every shape on a slide in document order, with groups opened up --
    SVG-compiled and designer-made decks keep most of their text inside
    groups."""
    from pptx.enum.shapes import MSO_SHAPE_TYPE

    for shape in shapes:
        if shape.shape_type == MSO_SHAPE_TYPE.GROUP:
            yield from leaf_shapes(shape.shapes)
        else:
            yield shape


def _chart_lines(shape: Any) -> list[str]:
    chart = shape.chart
    title = chart.chart_title.text_frame.text if chart.has_title else ""
    kind = str(chart.chart_type).split(" ")[0].split(".")[-1].lower()
    lines = [f"[chart {kind}{': ' + title if title else ''}]"]
    for plot in chart.plots:
        categories = [str(c) for c in plot.categories]
        for series in plot.series:
            values = ", ".join(
                f"{c} {_plain(v)}" for c, v in zip(categories, series.values, strict=False)
            )
            lines.append(f"  {series.name}: {values}")
    return lines


def _is_picture(shape: Any) -> bool:
    try:
        return shape.image is not None
    except (AttributeError, ValueError):
        return False


def _plain(value: Any) -> str:
    if value is None:
        return "-"
    return str(int(value)) if float(value).is_integer() else str(value)
