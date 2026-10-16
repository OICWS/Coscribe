"""Tool wrappers for shapes, formulas, tables, charts, hyperlinks and slide order."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Optional

from .toolkit import PresentationToolkit


def build_shapes_tools(toolkit: PresentationToolkit) -> dict[str, Callable[..., Any]]:
    def delete_pptx_slide(path: str, slide: int) -> dict[str, object]:
        """Remove one slide from an existing PowerPoint (.pptx) file --
        every other slide, and their order, is untouched.

        Args:
            path: path to an existing .pptx already in the workspace
            slide: 1-based slide index to delete
        """
        return toolkit.delete_pptx_slide(path=path, slide=slide)

    def duplicate_pptx_slide(
        path: str, slide: int, insert_at: Optional[int] = None  # noqa: UP045
    ) -> dict[str, object]:
        """Duplicate one slide in an existing PowerPoint (.pptx) file --
        every shape, its exact position/size/formatting, and every image
        on the source slide are copied. Speaker notes are not carried
        over to the copy.

        Args:
            path: path to an existing .pptx already in the workspace
            slide: 1-based slide index to duplicate
            insert_at: 1-based position for the new copy. Omit to insert
                it immediately after the source slide.
        """
        return toolkit.duplicate_pptx_slide(path=path, slide=slide, insert_at=insert_at)

    def reorder_pptx_slide(path: str, slide: int, new_position: int) -> dict[str, object]:
        """Move one slide to a new position in an existing PowerPoint
        (.pptx) file -- every slide's own content is untouched, only the
        deck's slide order changes.

        Args:
            path: path to an existing .pptx already in the workspace
            slide: 1-based slide index to move
            new_position: 1-based position to move it to
        """
        return toolkit.reorder_pptx_slide(path=path, slide=slide, new_position=new_position)

    def list_pptx_shapes(path: str, slide: int) -> dict[str, object]:
        """List every shape on one slide of an existing PowerPoint
        (.pptx) file -- index, type, position/size (inches), rotation, a
        short text preview, fill color (if it's a plain solid fill, as
        `"#RRGGBB"` or `"theme:ACCENT_1"`), whole-shape hyperlink if one
        is set, and whether it's real SmartArt (`is_smartart`) -- if so,
        `smartart_text` lists every node's own text, since neither this
        tool nor python-pptx can generate or edit real SmartArt (the
        layout algorithm lives in PowerPoint itself). See its text here,
        then delete_pptx_shape it and rebuild the idea with this file's
        other shape/icon/table tools if the user wants it replaced.

        Call this before edit_pptx_shape/delete_pptx_shape (or before
        editing a table's cells) on any slide you haven't already
        inspected. `shape_index` takes this list's `index`, a group
        member's `path` ("3/1": member 1 of the group at index 3, listed
        under its `members`) or a `name` only one shape has.

        Args:
            path: the .pptx file to inspect, relative to the workspace root
            slide: 1-based slide number to list shapes on
        """
        return toolkit.list_pptx_shapes(path=path, slide=slide)

    def delete_pptx_shape(path: str, slide: int, shape_index: str) -> dict[str, object]:
        """Remove one shape from an existing slide, in place -- every
        other shape and the rest of the deck are untouched. Works on any
        shape type (a plain autoshape/textbox, a picture, a table, a
        chart, or SmartArt).

        Call list_pptx_shapes first to find the right shape_index (this
        is that list's own `index`, 0-based) and confirm you're removing
        the right one -- this can't be undone by this tool. Real
        SmartArt's own node text (from that same list's `smartart_text`)
        is not preserved automatically; note it down before deleting if
        you'll need it to rebuild the idea with other shapes afterward.

        Args:
            path: file to modify, relative to the workspace root
            slide: 1-based slide number the shape is on
            shape_index: list_pptx_shapes's index, a member's path, or a name
        """
        return toolkit.delete_pptx_shape(path=path, slide=slide, shape_index=shape_index)

    def edit_pptx_shape(
        path: str,
        slide: int,
        shape_index: str,
        left_in: Optional[float] = None,  # noqa: UP045
        top_in: Optional[float] = None,  # noqa: UP045
        width_in: Optional[float] = None,  # noqa: UP045
        height_in: Optional[float] = None,  # noqa: UP045
        rotation: Optional[float] = None,  # noqa: UP045
        fill_color: str = "",
        fill_color_2: str = "",
        gradient_angle: Optional[float] = None,  # noqa: UP045
        text_color: str = "",
    ) -> dict[str, object]:
        """Move, resize, rotate, and/or recolor an existing shape (its
        fill and/or its text color) on an existing PowerPoint (.pptx)
        file's slide, without touching its text *content* or any other
        shape -- the tool for adjusting one element of an already-
        designed deck (a real uploaded template, or one coscribe already
        generated) rather than rebuilding the slide. A title/body
        placeholder is a shape like any other here -- find it via
        list_pptx_shapes and use text_color to recolor it.

        Call list_pptx_shapes(path, slide) first to find the right
        shape_index and confirm its current position/size/fill before
        changing it.

        Args:
            path: path to an existing .pptx already in the workspace
            slide: 1-based slide index the shape is on
            shape_index: list_pptx_shapes's index, a member's path, or a name
            left_in: new horizontal position in inches from the slide's
                left edge. Omit to leave unchanged.
            top_in: new vertical position in inches from the slide's top
                edge. Omit to leave unchanged.
            width_in: new width in inches. Omit to leave unchanged.
            height_in: new height in inches. Omit to leave unchanged.
            rotation: new rotation in degrees clockwise (0-360). Omit to
                leave unchanged.
            fill_color: new solid fill color, 6-hex-digit, no '#' (e.g.
                "38BDF8"). Omit to leave the fill unchanged. Only applies
                to a shape that has a fill (not a table/chart). Alone,
                sets a plain solid fill.
            fill_color_2: second gradient stop -- give this alongside
                fill_color for a two-stop linear gradient fill instead of
                solid (fill_color is the first stop). Omit for a solid fill.
            gradient_angle: gradient direction in degrees (0 = left-to-
                right, 90 = top-to-bottom, increasing clockwise). Only
                applies alongside fill_color_2; omit to keep the default
                90-degree top-to-bottom gradient.
            text_color: new color for every run of text already in the
                shape, 6-hex-digit, no '#'. Omit to leave text color
                unchanged. Only applies to a shape with a text frame
                (not a table/chart/picture). This is the tool for "make
                this title/paragraph a different color" -- changing a
                deck's theme accent color (edit_pptx_theme_colors)
                usually does NOT recolor plain title/body text, since
                that text typically doesn't reference the theme's accent
                color at all.
        """
        return toolkit.edit_pptx_shape(
            path=path,
            slide=slide,
            shape_index=shape_index,
            left_in=left_in,
            top_in=top_in,
            width_in=width_in,
            height_in=height_in,
            rotation=rotation,
            fill_color=fill_color,
            fill_color_2=fill_color_2,
            gradient_angle=gradient_angle,
            text_color=text_color,
        )

    def list_pptx_shape_types() -> list[str]:
        """List every shape_type name add_pptx_shape accepts -- a
        curated subset of python-pptx's full preset-geometry shape enum
        (basic shapes, arrows, flowchart nodes, callouts). No arguments:
        this is a static list, not specific to any file or slide."""
        return toolkit.list_pptx_shape_types()

    def add_pptx_shape(
        path: str,
        slide: int,
        shape_type: str,
        left_in: float,
        top_in: float,
        width_in: float,
        height_in: float,
        text: str = "",
        fill_color: str = "",
        line_color: str = "",
    ) -> dict[str, object]:
        """Add a new preset-geometry shape (an arrow, flowchart node,
        callout, or basic shape) onto an existing PowerPoint (.pptx)
        file's slide, at an exact position/size -- for building a
        specific diagram (a process flow of arrows and boxes, a
        comparison of callouts) shape by shape, unlike write_pptx's own
        icon-list/stat-callout layouts, which position their own shapes
        automatically.

        Call list_pptx_shape_types() first to see the available names.

        Args:
            path: path to an existing .pptx already in the workspace
            slide: 1-based slide index to add the shape to
            shape_type: one of list_pptx_shape_types()'s names, e.g.
                "RIGHT_ARROW", "FLOWCHART_DECISION", "ROUNDED_RECTANGLE"
            left_in: horizontal position in inches from the slide's left edge
            top_in: vertical position in inches from the slide's top edge
            width_in: shape width in inches
            height_in: shape height in inches
            text: optional text centered inside the shape (markdown
                **bold**/*italic* supported). Omit for no text.
            fill_color: optional solid fill color, 6-hex-digit, no '#'
                (e.g. "38BDF8"). Omit to keep the shape's default theme fill.
            line_color: optional outline color, 6-hex-digit, no '#'. Omit
                to keep the shape's default theme outline.
        """
        return toolkit.add_pptx_shape(
            path=path,
            slide=slide,
            shape_type=shape_type,
            left_in=left_in,
            top_in=top_in,
            width_in=width_in,
            height_in=height_in,
            text=text,
            fill_color=fill_color,
            line_color=line_color,
        )

    def add_pptx_formula(
        path: str,
        slide: int,
        latex: str,
        left_in: float,
        top_in: float,
        width_in: float,
        height_in: float,
        display: bool = True,
    ) -> dict[str, object]:
        """Add a real, natively-editable PowerPoint equation (the same
        Office Math object PowerPoint's own Insert > Equation creates)
        onto an existing PowerPoint (.pptx) file's slide, at an exact
        position/size -- for actual mathematical notation (fractions,
        roots, summations, matrices), not a text approximation typed
        with Unicode characters. Always creates a fresh text box
        containing exactly one formula, the same "new object at a
        position" shape as add_pptx_shape.

        `latex` is the documented Microsoft 365 LaTeX equation syntax --
        the same input PowerPoint's own equation editor accepts when you
        type LaTeX and press space. Unsupported/malformed LaTeX raises a
        clear error rather than a silent best-effort guess.

        Args:
            path: path to an existing .pptx already in the workspace
            slide: 1-based slide index to add the equation to
            latex: the LaTeX source for the equation, e.g.
                "\\frac{-b \\pm \\sqrt{b^2-4ac}}{2a}"
            left_in: horizontal position in inches from the slide's left edge
            top_in: vertical position in inches from the slide's top edge
            width_in: text box width in inches
            height_in: text box height in inches
            display: True (default) for a centered, standalone block
                equation; False for a smaller inline-sized expression.
        """
        return toolkit.add_pptx_formula(
            path=path,
            slide=slide,
            latex=latex,
            left_in=left_in,
            top_in=top_in,
            width_in=width_in,
            height_in=height_in,
            display=display,
        )

    def edit_pptx_table_cell(
        path: str, slide: int, shape_index: str, row: int, col: int, text: str
    ) -> dict[str, object]:
        """Replace one cell's text in an existing table on an existing
        PowerPoint (.pptx) file's slide, without touching any other cell
        or shape -- the tool for correcting/updating one value in an
        already-built table (a real uploaded template's table, or one
        coscribe already generated) instead of rebuilding the whole
        slide.

        Call list_pptx_shapes(path, slide) first to find the table's
        shape_index and its table_dimensions (rows/cols) -- row/col here
        are 0-based and must be within those dimensions.

        Args:
            path: path to an existing .pptx already in the workspace
            slide: 1-based slide index the table is on
            shape_index: list_pptx_shapes's index, a member's path, or a name
            row: 0-based row index of the cell to change
            col: 0-based column index of the cell to change
            text: new text for the cell, completely replacing its
                existing content
        """
        return toolkit.edit_pptx_table_cell(
            path=path, slide=slide, shape_index=shape_index, row=row, col=col, text=text
        )

    def merge_pptx_table_cells(
        path: str,
        slide: int,
        shape_index: str,
        start_row: int,
        start_col: int,
        end_row: int,
        end_col: int,
    ) -> dict[str, object]:
        """Merge a rectangular range of cells into one, in an existing
        table on an existing PowerPoint (.pptx) file's slide -- e.g. for
        a spanning header cell over several columns. Every merged-away
        cell's existing text is kept, appended as an extra paragraph
        into the resulting cell -- not discarded, so clear an unwanted
        cell's text with edit_pptx_table_cell first if you don't want it
        in the merged result.

        Call list_pptx_shapes(path, slide) first to find the table's
        shape_index and table_dimensions. Raises if the range already
        contains a merged cell.

        Args:
            path: path to an existing .pptx already in the workspace
            slide: 1-based slide index the table is on
            shape_index: list_pptx_shapes's index, a member's path, or a name
            start_row: 0-based row index of one corner of the range
            start_col: 0-based column index of one corner of the range
            end_row: 0-based row index of the opposite corner
            end_col: 0-based column index of the opposite corner
        """
        return toolkit.merge_pptx_table_cells(
            path=path,
            slide=slide,
            shape_index=shape_index,
            start_row=start_row,
            start_col=start_col,
            end_row=end_row,
            end_col=end_col,
        )

    def add_pptx_chart(
        path: str, slide: int, chart_type: str, data: str, title: str = ""
    ) -> dict[str, object]:
        """Add a chart to an existing slide in a PowerPoint (.pptx) file.

        `data` is a pipe-table (same convention as write_xlsx's content): the
        first column is the category axis, every other column is its own
        data series named from that column's header cell, e.g.:

            | Quarter | Revenue | Profit |
            | --- | --- | --- |
            | Q1 | 100 | 20 |
            | Q2 | 120 | 25 |

        `chart_type` is `"bar"`, `"line"`, or `"pie"` -- a pie chart takes
        exactly one data column (a second series has no meaningful
        rendering as pie slices).

        The response's `preview_path` (when the file can be drawn) names
        a rendered thumbnail of the slide the user can see in the chat UI --
        not something to fetch or parse yourself.

        Args:
            path: file to modify, relative to the workspace root
            slide: 1-based slide number to add the chart to
            chart_type: "bar", "line", or "pie"
            data: pipe-table rows as described above
            title: optional chart title
        """
        return toolkit.add_pptx_chart(
            path=path, slide=slide, chart_type=chart_type, data=data, title=title
        )

    def add_pptx_hyperlink(
        path: str, slide: int, shape_index: str, url: str, text: Optional[str] = None  # noqa: UP045
    ) -> dict[str, object]:
        """Add a clickable hyperlink to an external URL, either on a
        specific run of text or on a whole shape.

        Call `list_pptx_shapes` first to find `shape_index` (this is
        that list's own `index`, 0-based in on-slide order) and to see
        each shape's current `hyperlink` (None if it has none).

        If `text` is omitted, the *whole shape* becomes clickable (its
        `click_action` -- works on any shape: a picture, an icon, an
        autoshape, a table). If `text` is given, it must exactly match
        one whole text run's text within that shape's text frame (e.g.
        one word or phrase that has its own distinct formatting, or an
        entire short paragraph if it's all one run) -- the hyperlink is
        added to just that run, not the rest of the shape's text.
        Raises, listing the shape's actual run texts, if no run matches
        exactly; hyperlinking part of a run (a substring within it)
        isn't supported.

        `url` is either an external destination -- must start with
        "http://", "https://", "mailto:", or "ftp://" -- or `"#slide-N"`
        (1-based) to make this an *internal* "jump to slide N" navigation
        link instead, PowerPoint's own real click-action for this (not a
        generic external link to some internal address).

        This is pure `python-pptx` public API (`Run.hyperlink`/
        `Shape.click_action.hyperlink` for external URLs,
        `Shape.click_action.target_slide` for slide jumps), no
        hand-written XML.

        Args:
            path: file to modify, relative to the workspace root
            slide: 1-based slide number the shape is on
            shape_index: list_pptx_shapes's index, a member's path, or a name
            url: destination URL (e.g. "https://example.com") or
                "#slide-N" to jump to slide N within this presentation
            text: exact text of one run to hyperlink; omit to hyperlink
                the whole shape instead
        """
        return toolkit.add_pptx_hyperlink(
            path=path, slide=slide, shape_index=shape_index, url=url, text=text
        )

    return {
        "delete_pptx_slide": delete_pptx_slide,
        "duplicate_pptx_slide": duplicate_pptx_slide,
        "reorder_pptx_slide": reorder_pptx_slide,
        "list_pptx_shapes": list_pptx_shapes,
        "delete_pptx_shape": delete_pptx_shape,
        "edit_pptx_shape": edit_pptx_shape,
        "list_pptx_shape_types": list_pptx_shape_types,
        "add_pptx_shape": add_pptx_shape,
        "add_pptx_formula": add_pptx_formula,
        "edit_pptx_table_cell": edit_pptx_table_cell,
        "merge_pptx_table_cells": merge_pptx_table_cells,
        "add_pptx_chart": add_pptx_chart,
        "add_pptx_hyperlink": add_pptx_hyperlink,
    }
