"""How `list_pptx_shapes` describes one shape: its kind, geometry, fill, text and links."""

from __future__ import annotations

from typing import Any

from .smartart import is_smartart, smartart_text


def _describe_fill_color(color: Any) -> str | None:
    """One `ColorFormat`'s own value as `"#RRGGBB"`/`"theme:ACCENT_1"` --
    the shared per-color logic `_describe_shape_fill` uses for both a
    solid fill's single color and a gradient fill's two-or-more stops."""
    from pptx.enum.dml import MSO_COLOR_TYPE

    if color.type == MSO_COLOR_TYPE.SCHEME:
        return f"theme:{color.theme_color.name}"
    if color.type == MSO_COLOR_TYPE.RGB:
        return f"#{color.rgb}"
    return None


def _describe_shape_fill(shape: Any) -> str | dict[str, object] | None:
    """A shape's fill: a solid fill's color as `"#RRGGBB"` (literal) or
    `"theme:ACCENT_1"` (a `theme_color` reference); a gradient fill (see
    `edit_pptx_shape`'s `fill_color_2`) as `{"type": "gradient", "colors":
    [...], "angle": <degrees or None>}`, one entry in `colors` per stop,
    in gradient order -- lets a model confirm what it just set via
    `list_pptx_shapes` the same way it can for a solid color. `None` when
    the shape has no fill concept at all (a table/chart `GraphicFrame`,
    which has no `.fill` attribute), no fill set, or a picture/pattern
    fill (out of scope -- `list_pptx_shapes` only needs enough to target
    or verify a plain accent-colored/gradient shape, not describe every
    fill type OOXML supports)."""
    from pptx.enum.dml import MSO_FILL

    fill = getattr(shape, "fill", None)
    if fill is None:
        return None
    try:
        fill_type = fill.type
    except (AttributeError, TypeError):
        return None
    if fill_type == MSO_FILL.GRADIENT:
        angle: float | None
        try:
            angle = fill.gradient_angle
        except ValueError:
            angle = None  # non-linear (e.g. radial) -- angle doesn't apply
        except TypeError:
            # Real python-pptx bug, hit live while testing this: a fresh
            # `fill.gradient()`'s <a:lin> element has no `ang` attribute
            # at all (angle "inherited"), and gradient_angle's own getter
            # does `360.0 - None` in that case instead of treating it the
            # same as no <a:lin> at all. edit_pptx_shape works around this
            # by always setting an explicit angle after calling
            # `.gradient()` (see below), but a gradient from an externally
            # -authored file could still hit this, so this is defensive
            # here too, not just relying on that workaround.
            angle = None
        return {
            "type": "gradient",
            "colors": [_describe_fill_color(stop.color) for stop in fill.gradient_stops],
            "angle": angle,
        }
    if fill_type != MSO_FILL.SOLID:
        return None
    return _describe_fill_color(fill.fore_color)


def describe_shape(index: int | str, shape: Any) -> dict[str, object]:
    """One `list_pptx_shapes` entry -- enough for a text-only model to
    pick a target (`shape_index`) for `edit_pptx_shape`/`replace_pptx_image`/
    the table-cell-editing tools without guessing: type, a short text
    preview, position/size in inches (matching `edit_pptx_shape`'s own
    `*_in` parameters), rotation, fill color if it's a plain solid fill,
    whole-shape hyperlink address (matching `add_pptx_hyperlink`'s own
    whole-shape mode) if one is set -- `"#slide-N"` for an internal slide
    jump, same syntax `add_pptx_hyperlink`'s own `url` accepts, not the
    raw internal relationship target -- and whether it's real SmartArt
    (`is_smartart`) -- if so, `smartart_text` lists every node's own
    text, since neither python-pptx nor this tool can generate or edit
    real SmartArt (the layout algorithm lives in PowerPoint itself, not
    the file format); this is what lets a model see what a diagram
    actually said before deciding how to rebuild the slide with this
    file's other tools."""
    from pptx.enum.shapes import MSO_SHAPE_TYPE

    hyperlink: str | None
    is_group = shape.shape_type == MSO_SHAPE_TYPE.GROUP  # click_action raises TypeError
    try:
        jump_target = None if is_group else shape.click_action.target_slide
    except ValueError:
        # A real, if unusual, PowerPoint construct this tool never
        # writes itself but must not crash reading back: a "next
        # slide"/"previous slide" navigation action on the last/first
        # slide, where python-pptx's own target_slide resolution raises
        # rather than returning None.
        jump_target = None
    if jump_target is not None:
        slides = shape.part.package.presentation_part.presentation.slides
        # The same "#slide-N" syntax add_pptx_hyperlink's own `url`
        # accepts -- reading this field back and feeding it straight into
        # another add_pptx_hyperlink call must round-trip, not show the
        # raw internal relationship target (e.g. "slide2.xml", which
        # isn't even guaranteed to match display order after slides are
        # reordered/duplicated).
        hyperlink = f"#slide-{slides.index(jump_target) + 1}"
    else:
        hyperlink = None if is_group else shape.click_action.hyperlink.address
    text_preview: str | None = None
    if shape.has_text_frame:
        text = shape.text_frame.text.strip()
        if text:
            text_preview = text if len(text) <= 80 else text[:77] + "..."
    smartart = is_smartart(shape)
    info: dict[str, object] = {
        "index": index,
        "name": shape.name,
        "shape_type": str(shape.shape_type) if shape.shape_type is not None else None,
        "left_in": emu_to_inches(shape.left),
        "top_in": emu_to_inches(shape.top),
        "width_in": emu_to_inches(shape.width),
        "height_in": emu_to_inches(shape.height),
        "rotation": shape.rotation,
        "is_placeholder": shape.is_placeholder,
        "is_table": shape.has_table,
        "is_picture": shape.shape_type == MSO_SHAPE_TYPE.PICTURE,
        "is_smartart": smartart,
        "smartart_text": smartart_text(shape) if smartart else None,
        "text_preview": text_preview,
        "fill": _describe_shape_fill(shape),
        "hyperlink": hyperlink,
    }
    if shape.has_table:
        table = shape.table
        info["table_dimensions"] = {"rows": len(table.rows), "cols": len(table.columns)}
    return info


def emu_to_inches(value: int | None) -> float | None:
    return round(value / 914400, 2) if value is not None else None
