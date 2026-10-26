"""The deck tools as plain functions over one toolkit, with the descriptions the model reads."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any, Literal

from ....runtime import tool_metadata
from .toolkit import PresentationToolkit
from .wrappers_design import build_design_tools
from .wrappers_images import build_images_tools
from .wrappers_review import build_review_tools
from .wrappers_shapes import build_shapes_tools
from .wrappers_templates import build_templates_tools
from .wrappers_xml_animation import build_xml_animation_tools

# Tool order and risk, fixed: the tool list is provider-cached, so a reorder costs a cache miss.
_TOOLS: tuple[tuple[str, Literal["READ", "WRITE_LOCAL"]], ...] = (
    ("read_pptx", "READ"),
    ("render_pptx_preview", "READ"),
    ("write_pptx", "WRITE_LOCAL"),
    ("fill_pptx_template", "WRITE_LOCAL"),
    ("extract_pptx_template", "WRITE_LOCAL"),
    ("edit_pptx_text", "WRITE_LOCAL"),
    ("delete_pptx_slide", "WRITE_LOCAL"),
    ("duplicate_pptx_slide", "WRITE_LOCAL"),
    ("reorder_pptx_slide", "WRITE_LOCAL"),
    ("list_pptx_shapes", "READ"),
    ("edit_pptx_shape", "WRITE_LOCAL"),
    ("delete_pptx_shape", "WRITE_LOCAL"),
    ("list_pptx_shape_types", "READ"),
    ("add_pptx_shape", "WRITE_LOCAL"),
    ("add_pptx_formula", "WRITE_LOCAL"),
    ("replace_pptx_image", "WRITE_LOCAL"),
    ("crop_pptx_image", "WRITE_LOCAL"),
    ("list_pptx_icons", "READ"),
    ("add_pptx_icon", "WRITE_LOCAL"),
    ("recolor_pptx_icon", "WRITE_LOCAL"),
    ("edit_pptx_table_cell", "WRITE_LOCAL"),
    ("merge_pptx_table_cells", "WRITE_LOCAL"),
    ("add_pptx_chart", "WRITE_LOCAL"),
    ("add_pptx_image", "WRITE_LOCAL"),
    ("set_pptx_background_image", "WRITE_LOCAL"),
    ("add_pptx_scrim", "WRITE_LOCAL"),
    ("add_pptx_shape_effect", "WRITE_LOCAL"),
    ("read_pptx_xml", "READ"),
    ("edit_pptx_xml", "WRITE_LOCAL"),
    ("set_pptx_notes", "WRITE_LOCAL"),
    ("set_pptx_transition", "WRITE_LOCAL"),
    ("list_pptx_transition_types", "READ"),
    ("add_pptx_animation", "WRITE_LOCAL"),
    ("list_pptx_animation_types", "READ"),
    ("add_pptx_audio", "WRITE_LOCAL"),
    ("add_pptx_hyperlink", "WRITE_LOCAL"),
    ("check_pptx_delivery", "READ"),
    ("read_pptx_theme_colors", "READ"),
    ("edit_pptx_theme_colors", "WRITE_LOCAL"),
    ("read_pptx_design", "READ"),
)


def build_presentation_tools(
    root: str | Path,
    *,
    state_dir: str | Path | None = None,
    custom_templates_dir: str | Path | None = None,
    extra_readable: Sequence[str | Path] = (),
    extra_writable: Sequence[str | Path] = (),
) -> list[Callable[..., Any]]:
    """Return the tool callables the Coordinator agent can call, bound to `root`
    (plus any user-configured extra_readable/extra_writable directories)."""
    toolkit = PresentationToolkit(
        root,
        state_dir=state_dir,
        custom_templates_dir=custom_templates_dir,
        extra_readable=extra_readable,
        extra_writable=extra_writable,
    )
    tools = {
        **build_design_tools(toolkit),
        **build_images_tools(toolkit),
        **build_review_tools(toolkit),
        **build_shapes_tools(toolkit),
        **build_templates_tools(toolkit),
        **build_xml_animation_tools(toolkit),
    }
    return [
        tool_metadata(tools[name], risk_category=risk, category="documents")
        for name, risk in _TOOLS
    ]
