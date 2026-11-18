"""Toolkit methods for shapes, formulas, tables, charts, hyperlinks and slide order."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Optional

from ..._chart_data import CHART_TYPES, parse_chart_table
from ..._file_locks import locked_by_path
from ..._ooxml_validate import assert_ooxml_valid
from ..._pptx_shapes import describe_members, set_slide_box
from ..._thumbnail import render_thumbnail
from . import slide_builders as sb
from . import toolkit_helpers as th
from .qa import (
    shape_bbox,
)
from .shape_description import describe_shape as _describe_shape
from .shape_description import emu_to_inches
from .template_slides import duplicate_slide_part
from .theme import (
    THEME_HEX_RE,
    read_scheme_color,
)
from .toolkit_base import ToolkitBase
from .transitions import (
    mark_mce_ignorable,
)
from .xmlns import (
    A14_NS,
)

if TYPE_CHECKING:
    pass


class ShapeToolsMixin(ToolkitBase):
    @locked_by_path
    def list_pptx_shapes(self, path: str, slide: int) -> dict[str, object]:
        """Structured inventory of every shape on one slide of an
        existing .pptx -- index, type, position/size, rotation, a short
        text preview, and fill color if it's a plain solid fill. Call
        this before `edit_pptx_shape` (or any table-editing tool) on a
        slide you haven't inspected yet: `shape_index` there is this
        list's own `index`, and guessing it blind on a slide with
        several shapes is exactly the failure mode this tool exists to
        avoid.

        `slide_width_in`/`slide_height_in` are the whole deck's own
        canvas size (every slide in one .pptx shares one size) -- besides
        being useful context for reasoning about layout, this is also
        what web/app.py's GET /api/pptx-shapes (the click-to-target-a-
        shape preview feature) uses to turn each shape's inch-based
        bbox into an on-screen percentage overlay, independent of
        whatever pixel size the rendered preview image happens to be."""
        from pptx import Presentation

        file_path = self._check_readable(path)
        prs = Presentation(str(file_path))
        slide_count = len(prs.slides)
        if not 1 <= slide <= slide_count:
            raise ValueError(f"Slide {slide} out of range: deck has {slide_count} slides")
        target_slide = prs.slides[slide - 1]
        from pptx.enum.shapes import MSO_SHAPE_TYPE

        shapes = [_describe_shape(index, shape) for index, shape in enumerate(target_slide.shapes)]
        for info, shape in zip(shapes, target_slide.shapes, strict=True):
            if shape.shape_type == MSO_SHAPE_TYPE.GROUP:
                info["members"] = describe_members(shape, str(info["index"]), _describe_shape)
        return {
            "slide": slide,
            "shape_count": len(shapes),
            "shapes": shapes,
            "slide_width_in": emu_to_inches(prs.slide_width),
            "slide_height_in": emu_to_inches(prs.slide_height),
        }

    @locked_by_path
    def edit_pptx_shape(
        self,
        path: str,
        slide: int,
        shape_index: int | str,
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
        """Change an existing shape's geometry, fill color, and/or text
        color in place, on any already-existing .pptx -- call
        `list_pptx_shapes` first to find `shape_index` (this is that
        list's own `index`, 0-based in on-slide order) and confirm
        you're targeting the right shape; text *content*, other shapes,
        and the rest of the deck are untouched. Every parameter is
        optional -- only the ones given are changed.

        `fill_color` alone sets a plain solid fill, same as before. Give
        `fill_color_2` too for a two-stop linear gradient (`fill_color`
        is the first stop, `fill_color_2` the second) -- real OOXML
        `<a:gradFill>` via python-pptx's own native gradient API, not a
        picture or hand-built XML. `gradient_angle` (degrees, 0 =
        left-to-right, 90 = top-to-bottom, increasing clockwise) only
        applies alongside `fill_color_2`; omit it to keep python-pptx's
        own default 90-degree (top-to-bottom) gradient.

        `text_color` recolors every run of text already inside the
        shape (a title/body placeholder counts -- it's a shape like any
        other via `list_pptx_shapes`) -- this is the tool for "make this
        title/paragraph a different color," not `edit_pptx_theme_colors`
        (see that tool's own docstring: changing a theme accent color
        only recolors elements that explicitly *reference* that theme
        color -- coscribe's own decorative shapes and, just as often,
        plain title/body text, do not -- so it routinely leaves text
        exactly the color it already was)."""
        from pptx.dml.color import RGBColor
        from pptx.util import Inches

        if fill_color_2 and not fill_color:
            raise ValueError(
                "edit_pptx_shape: fill_color_2 needs fill_color too -- fill_color "
                "is the gradient's first stop, fill_color_2 its second."
            )
        if gradient_angle is not None and not fill_color_2:
            raise ValueError(
                "edit_pptx_shape: gradient_angle only applies alongside a "
                "two-color gradient fill -- pass fill_color_2 too."
            )
        if (
            left_in is None
            and top_in is None
            and width_in is None
            and height_in is None
            and rotation is None
            and not fill_color
            and not text_color
        ):
            raise ValueError(
                "edit_pptx_shape needs at least one property to change (position, "
                "size, rotation, fill_color, or text_color)."
            )
        if fill_color and not THEME_HEX_RE.match(fill_color):
            raise ValueError(
                f"fill_color {fill_color!r} must be a 6-hex-digit color (no '#'), e.g. '38BDF8'."
            )
        if fill_color_2 and not THEME_HEX_RE.match(fill_color_2):
            raise ValueError(
                f"fill_color_2 {fill_color_2!r} must be a 6-hex-digit color (no '#'), "
                f"e.g. '38BDF8'."
            )
        if text_color and not THEME_HEX_RE.match(text_color):
            raise ValueError(
                f"text_color {text_color!r} must be a 6-hex-digit color (no '#'), e.g. '38BDF8'."
            )
        prs, file_path, target_slide = self._open_slide(path, slide)
        shape = th.get_shape_at_index(target_slide, slide, shape_index)
        box = [None if v is None else Inches(v) for v in (left_in, top_in, width_in, height_in)]
        set_slide_box(shape, *box)
        if rotation is not None:
            shape.rotation = rotation
        if fill_color:
            fill = getattr(shape, "fill", None)
            if fill is None:
                raise ValueError(
                    f"Shape {shape_index} on slide {slide} ({shape.shape_type}) has no "
                    f"fill to set -- fill_color only applies to a shape with a fill "
                    f"(not a table/chart)."
                )
            if fill_color_2:
                fill.gradient()
                stops = fill.gradient_stops
                stops[0].color.rgb = RGBColor.from_string(fill_color)  # type: ignore[no-untyped-call]
                stops[1].color.rgb = RGBColor.from_string(fill_color_2)  # type: ignore[no-untyped-call]
                # Always set an explicit angle, not just when the caller
                # gave one -- a fresh `fill.gradient()`'s <a:lin> element
                # has no `ang` attribute at all, and python-pptx's own
                # gradient_angle *getter* crashes with a TypeError trying
                # to read that back (`360.0 - None`), confirmed live while
                # testing this. 90.0 matches gradient()'s own documented
                # default (top-to-bottom) -- this just makes that default
                # actually readable afterward instead of only writable.
                fill.gradient_angle = gradient_angle if gradient_angle is not None else 90.0
            else:
                fill.solid()
                fill.fore_color.rgb = RGBColor.from_string(fill_color)  # type: ignore[no-untyped-call]
        if text_color:
            if not shape.has_text_frame:
                raise ValueError(
                    f"Shape {shape_index} on slide {slide} ({shape.shape_type}) has no "
                    f"text to color -- text_color only applies to a shape with a text "
                    f"frame (not a table/chart/picture)."
                )
            rgb = RGBColor.from_string(text_color)  # type: ignore[no-untyped-call]
            for paragraph in shape.text_frame.paragraphs:
                for run in paragraph.runs:
                    run.font.color.rgb = rgb
        prs.save(str(file_path))

        return {
            "path": self._scope.relative(file_path),
            "slide": slide,
            "shape_index": shape_index,
            "shape": _describe_shape(shape_index, shape),
        }

    @locked_by_path
    def delete_pptx_shape(self, path: str, slide: int, shape_index: int | str) -> dict[str, object]:
        prs, file_path, target_slide = self._open_slide(path, slide)
        shape = th.get_shape_at_index(target_slide, slide, shape_index)
        element = shape._element  # noqa: SLF001
        element.getparent().remove(element)
        prs.save(str(file_path))
        return {"path": self._scope.relative(file_path), "slide": slide, "shape_index": shape_index}

    def list_pptx_shape_types(self) -> list[str]:
        """Every `shape_type` name `add_pptx_shape` accepts, sorted -- a
        curated subset of python-pptx's full MSO_SHAPE enum (basic
        shapes, arrows, flowchart nodes, callouts). No path/slide
        argument: this is a static list, the same regardless of which
        file or slide you're working on."""
        return sorted(th.SHAPE_TYPES)

    @locked_by_path
    def add_pptx_shape(
        self,
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
        callout, or basic shape -- call `list_pptx_shape_types()` for
        the full curated set) onto an existing slide, at the exact
        position/size you give -- unlike write_pptx's own icon-list/
        stat-callout layouts, which position their own shapes
        automatically, this is for building a specific diagram (a
        process flow of arrows and boxes, a comparison of callouts)
        shape by shape. `text`, if given, is centered inside the shape
        (markdown `**bold**`/`*italic*` supported, same as every other
        text tool in this file). `fill_color`/`line_color` are
        6-hex-digit colors (no '#'); omit either to keep the shape's own
        default theme styling. Returns the new shape's own
        `shape_index` -- pass it straight to `edit_pptx_shape`/
        `add_pptx_hyperlink`/`delete_pptx_shape` to keep working on it."""
        from pptx.dml.color import RGBColor
        from pptx.enum.shapes import MSO_SHAPE
        from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
        from pptx.util import Inches

        if shape_type not in th.SHAPE_TYPES:
            raise ValueError(
                f"Unknown shape_type {shape_type!r} -- call list_pptx_shape_types() "
                f"to see the available names."
            )
        if fill_color and not THEME_HEX_RE.match(fill_color):
            raise ValueError(
                f"fill_color {fill_color!r} must be a 6-hex-digit color (no '#'), e.g. '38BDF8'."
            )
        if line_color and not THEME_HEX_RE.match(line_color):
            raise ValueError(
                f"line_color {line_color!r} must be a 6-hex-digit color (no '#'), e.g. '38BDF8'."
            )
        prs, file_path, target_slide = self._open_slide(path, slide)
        shape = target_slide.shapes.add_shape(
            getattr(MSO_SHAPE, shape_type),
            Inches(left_in),
            Inches(top_in),
            Inches(width_in),
            Inches(height_in),
        )
        if text:
            text_frame = shape.text_frame
            text_frame.word_wrap = True
            text_frame.vertical_anchor = MSO_ANCHOR.MIDDLE
            paragraph = text_frame.paragraphs[0]
            paragraph.alignment = PP_ALIGN.CENTER
            sb.add_inline_runs(paragraph, text)
        if fill_color:
            shape.fill.solid()
            shape.fill.fore_color.rgb = RGBColor.from_string(fill_color)  # type: ignore[no-untyped-call]
        if line_color:
            shape.line.color.rgb = RGBColor.from_string(line_color)  # type: ignore[no-untyped-call]
        shape_index = len(target_slide.shapes) - 1
        prs.save(str(file_path))

        state_dir = Path(self._state_dir) if self._state_dir is not None else None
        preview_path, preview_skipped_reason = render_thumbnail(file_path, state_dir)
        return {
            "path": self._scope.relative(file_path),
            "slide": slide,
            "shape_type": shape_type,
            "shape_index": shape_index,
            "preview_path": preview_path,
            "preview_skipped_reason": preview_skipped_reason,
        }

    @locked_by_path
    def add_pptx_formula(
        self,
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
        onto an existing slide, at the exact position/size you give --
        for actual mathematical notation (fractions, roots, summations,
        matrices), not a text approximation typed with Unicode
        characters. Always creates a fresh text box containing exactly
        one formula, the same "new object at a position" shape as
        add_pptx_shape above -- for a formula that belongs alongside
        other text in an existing paragraph, this isn't that (v1 scope).

        `latex` is the documented Microsoft 365 LaTeX equation syntax --
        the same input PowerPoint's own equation editor accepts when you
        type LaTeX and press space, e.g.
        r"\\frac{-b \\pm \\sqrt{b^2-4ac}}{2a}". Unsupported/malformed LaTeX
        raises ValueError with the real compiler error, not a silent
        best-effort guess.

        Args:
            path: path to an existing .pptx already in the workspace
            slide: 1-based slide index to add the equation to
            latex: the LaTeX source for the equation
            left_in: horizontal position in inches from the slide's left edge
            top_in: vertical position in inches from the slide's top edge
            width_in: text box width in inches
            height_in: text box height in inches
            display: True (default) for a centered, standalone block
                equation; False for a smaller inline-sized expression.
        """
        from lxml import etree
        from pptx.util import Inches

        from ..._native_formula import (
            FormulaCompileError,
            compile_latex_to_inline_omml,
            compile_latex_to_omml,
        )

        try:
            omml_xml = (
                compile_latex_to_omml(latex) if display else compile_latex_to_inline_omml(latex)
            )
        except FormulaCompileError as exc:
            raise ValueError(f"Could not compile LaTeX formula {latex!r}: {exc}") from exc

        prs, file_path, target_slide = self._open_slide(path, slide)
        shape = target_slide.shapes.add_textbox(
            Inches(left_in), Inches(top_in), Inches(width_in), Inches(height_in)
        )
        paragraph = shape.text_frame.paragraphs[0]
        p_element = paragraph._p  # noqa: SLF001
        # `<a14:m>` wrapping `<m:oMathPara>`/`<m:oMath>` -- the exact shape
        # hugohe3/ppt-master's own documented contract uses (see A14_NS's
        # comment above). A fresh text box's first paragraph has no runs
        # yet, so this is simply appended as the paragraph's sole content.
        math_root = etree.fromstring(omml_xml.encode("utf-8"))
        a14_wrapper = etree.SubElement(p_element, f"{{{A14_NS}}}m", nsmap={"a14": A14_NS})
        a14_wrapper.append(math_root)

        mark_mce_ignorable(target_slide.element, "a14")
        assert_ooxml_valid(target_slide.element, "add_pptx_formula")
        prs.save(str(file_path))

        shape_index = len(target_slide.shapes) - 1
        state_dir = Path(self._state_dir) if self._state_dir is not None else None
        preview_path, preview_skipped_reason = render_thumbnail(file_path, state_dir)
        return {
            "path": self._scope.relative(file_path),
            "slide": slide,
            "shape_index": shape_index,
            "display": display,
            "preview_path": preview_path,
            "preview_skipped_reason": preview_skipped_reason,
        }

    @locked_by_path
    def edit_pptx_table_cell(
        self, path: str, slide: int, shape_index: int | str, row: int, col: int, text: str
    ) -> dict[str, object]:
        """Replace one cell's text in an existing table, in place, on
        any already-existing .pptx -- call `list_pptx_shapes` first to
        find the table's `shape_index` and its `table_dimensions`
        (rows/cols); `row`/`col` are 0-based. Every other cell, and the
        rest of the deck, is untouched."""
        prs, file_path, target_slide = self._open_slide(path, slide)
        shape = th.get_table_shape(target_slide, slide, shape_index)
        table = shape.table
        n_rows, n_cols = len(table.rows), len(table.columns)
        if not 0 <= row < n_rows or not 0 <= col < n_cols:
            raise ValueError(
                f"cell (row={row}, col={col}) out of range: table has {n_rows} row(s) "
                f"x {n_cols} column(s) -- call list_pptx_shapes first to confirm "
                f"table_dimensions."
            )
        cell = table.cell(row, col)
        # .clear() first -- same reasoning as sb.set_title/sb.fill_content_placeholder:
        # this REPLACES the cell's existing content instead of appending onto it.
        cell.text_frame.clear()
        sb.add_inline_runs(cell.text_frame.paragraphs[0], text)
        prs.save(str(file_path))

        return {
            "path": self._scope.relative(file_path),
            "slide": slide,
            "shape_index": shape_index,
            "row": row,
            "col": col,
        }

    @locked_by_path
    def merge_pptx_table_cells(
        self,
        path: str,
        slide: int,
        shape_index: int | str,
        start_row: int,
        start_col: int,
        end_row: int,
        end_col: int,
    ) -> dict[str, object]:
        """Merge a rectangular range of cells in an existing table into
        one, on any already-existing .pptx -- (start_row, start_col) and
        (end_row, end_col) are opposite corners of the range (either
        diagonal, either order), 0-based. Every merged-away cell's
        existing text is kept, appended into the resulting cell as an
        extra paragraph (python-pptx's own merge behavior, verified
        live) -- not discarded, so clear an unwanted cell's text with
        `edit_pptx_table_cell` first if that's not wanted in the merged
        result. Call `list_pptx_shapes` first to find the table's
        `shape_index` and `table_dimensions`. Raises if the range
        already contains a
        merged cell."""
        prs, file_path, target_slide = self._open_slide(path, slide)
        shape = th.get_table_shape(target_slide, slide, shape_index)
        table = shape.table
        n_rows, n_cols = len(table.rows), len(table.columns)
        for row, col, label in (
            (start_row, start_col, "start_row/start_col"),
            (end_row, end_col, "end_row/end_col"),
        ):
            if not 0 <= row < n_rows or not 0 <= col < n_cols:
                raise ValueError(
                    f"{label} (row={row}, col={col}) out of range: table has "
                    f"{n_rows} row(s) x {n_cols} column(s) -- call list_pptx_shapes "
                    f"first to confirm table_dimensions."
                )
        table.cell(start_row, start_col).merge(table.cell(end_row, end_col))
        prs.save(str(file_path))

        return {
            "path": self._scope.relative(file_path),
            "slide": slide,
            "shape_index": shape_index,
            "merged_range": {
                "start_row": start_row,
                "start_col": start_col,
                "end_row": end_row,
                "end_col": end_col,
            },
        }

    @locked_by_path
    def delete_pptx_slide(self, path: str, slide: int) -> dict[str, object]:
        """Remove one slide from an existing .pptx, in place -- every
        other slide, and their own order, is untouched. Same drop-the-
        relationship-then-remove-the-list-entry mechanism `sb.clear_slides`
        already uses when write_pptx builds on a `template_path`."""
        from pptx.oxml.ns import qn

        prs, file_path, _target_slide = self._open_slide(path, slide)
        sld_id_lst = prs.slides._sldIdLst  # noqa: SLF001
        sld_id_element = list(sld_id_lst)[slide - 1]
        r_id = sld_id_element.get(qn("r:id"))
        prs.part.drop_rel(r_id)
        sld_id_lst.remove(sld_id_element)
        prs.save(str(file_path))

        return {
            "path": self._scope.relative(file_path),
            "deleted_slide": slide,
            "slide_count": len(prs.slides),
        }

    @locked_by_path
    def duplicate_pptx_slide(
        self,
        path: str,
        slide: int,
        insert_at: Optional[int] = None,  # noqa: UP045
    ) -> dict[str, object]:
        """Duplicate one slide in an existing .pptx, in place -- every
        shape, its exact position/size/formatting, and every image the
        source slide has are copied. Speaker notes are not (see
        `duplicate_slide_part`'s docstring). Defaults to inserting the
        copy immediately after the source; pass `insert_at` (1-based) to
        place it elsewhere instead."""
        prs, file_path, source_slide = self._open_slide(path, slide)
        slide_count = len(prs.slides)
        target_position = insert_at if insert_at is not None else slide + 1
        if not 1 <= target_position <= slide_count + 1:
            raise ValueError(
                f"insert_at {target_position} out of range: deck has {slide_count} "
                f"slide(s), valid positions are 1 to {slide_count + 1}."
            )
        new_rid = duplicate_slide_part(prs, source_slide)
        sld_id_lst = prs.slides._sldIdLst  # noqa: SLF001
        new_sld_id = sld_id_lst.add_sldId(new_rid)
        sld_id_lst.remove(new_sld_id)
        sld_id_lst.insert(target_position - 1, new_sld_id)
        prs.save(str(file_path))

        return {
            "path": self._scope.relative(file_path),
            "source_slide": slide,
            "new_slide": target_position,
            "slide_count": len(prs.slides),
        }

    @locked_by_path
    def reorder_pptx_slide(self, path: str, slide: int, new_position: int) -> dict[str, object]:
        """Move one slide to a new 1-based position in an existing
        .pptx, in place -- every slide's own content is untouched, only
        the deck's slide order changes."""
        prs, file_path, _target_slide = self._open_slide(path, slide)
        slide_count = len(prs.slides)
        if not 1 <= new_position <= slide_count:
            raise ValueError(
                f"new_position {new_position} out of range: deck has {slide_count} slide(s)."
            )
        sld_id_lst = prs.slides._sldIdLst  # noqa: SLF001
        sld_id_element = list(sld_id_lst)[slide - 1]
        sld_id_lst.remove(sld_id_element)
        sld_id_lst.insert(new_position - 1, sld_id_element)
        prs.save(str(file_path))

        return {
            "path": self._scope.relative(file_path),
            "old_position": slide,
            "new_position": new_position,
        }

    @locked_by_path
    def add_pptx_chart(
        self, path: str, slide: int, chart_type: str, data: str, title: str = ""
    ) -> dict[str, object]:
        from pptx.chart.data import CategoryChartData
        from pptx.enum.chart import XL_CHART_TYPE
        from pptx.opc.constants import RELATIONSHIP_TYPE as RT

        if chart_type not in CHART_TYPES:
            raise ValueError(
                f"Unknown chart_type {chart_type!r}. Use one of: {', '.join(sorted(CHART_TYPES))}"
            )
        categories, series = parse_chart_table(data, "add_pptx_chart")
        if chart_type == "pie" and len(series) > 1:
            raise ValueError("pie charts take exactly one data column plus the category column")

        prs, file_path, target_slide = self._open_slide(path, slide)

        # python-pptx's chart_data submodule ships no return-type annotations
        # on these two methods (unlike the rest of the library, which does),
        # so strict mode sees them as untyped calls -- confirmed there's no
        # types-python-pptx package on PyPI to fill the gap.
        chart_data = CategoryChartData()  # type: ignore[no-untyped-call]
        chart_data.categories = categories
        for name, values in series.items():
            chart_data.add_series(name, values)  # type: ignore[no-untyped-call]

        chart_xl_type = {
            "bar": XL_CHART_TYPE.COLUMN_CLUSTERED,
            "line": XL_CHART_TYPE.LINE,
            "pie": XL_CHART_TYPE.PIE,
        }[chart_type]

        # Real, live-reproduced defect this avoids: a fixed Inches(1, 1.6,
        # 8, 5) box ignored both the deck's real slide size (leaving a lot
        # of unused space on a widescreen deck) and any text already on the
        # slide's own body/content placeholder, so a chart added next to a
        # short intro sentence rendered directly on top of it. Default to
        # the same content-area geometry every other content slide uses.
        left, top, width, height = sb.content_area(prs)
        slide_height = prs.slide_height or 6858000
        body_placeholder = sb.find_body_placeholder(target_slide)
        if (
            body_placeholder is not None
            and body_placeholder.has_text_frame
            and body_placeholder.text_frame.text.strip()
        ):
            body_bbox = shape_bbox(body_placeholder)
            if body_bbox is not None:
                b_left, b_top, b_width, b_height = body_bbox
                # Shrink the placeholder to fit its own text instead of
                # trusting its full box height -- a *second* real,
                # live-reproduced defect this fixes: a stock "Title and
                # Content" layout's body placeholder is boxed generously
                # enough for a full bullet list regardless of how little
                # text it actually holds, so computing the chart's
                # position from that oversized box left almost no room
                # and pushed the chart off the bottom of the slide
                # entirely. One paragraph's worth of space per actual
                # paragraph is a rough but bounded estimate (doesn't
                # account for a paragraph wrapping across multiple visual
                # lines, since nothing in this sandbox can render text to
                # measure that precisely) -- good enough for the realistic
                # case this exists for (a short intro line/caption above a
                # chart), not a general-purpose text layout engine.
                paragraph_count = max(len(body_placeholder.text_frame.paragraphs), 1)
                per_paragraph_height = int(slide_height * 0.06)
                intro_height = min(b_height, per_paragraph_height * paragraph_count)
                # A THIRD real, live-reproduced defect, more severe than
                # the first two: this placeholder never had its own
                # <a:xfrm> (it inherits position/size from the layout, the
                # normal state for an unmoved placeholder) -- setting
                # `.height` alone makes python-pptx create a *new*, mostly
                # empty <a:xfrm> with only <a:ext cy=...> populated,
                # leaving width at 0 and the offset missing entirely. The
                # actual, live result: the placeholder rendered as a
                # near-zero-width sliver, wrapping to one character per
                # line and spilling off the edge of the slide -- caught
                # from a real rendered screenshot, not found by any
                # automated check (a 0-width shape still "has" a bbox, so
                # check_text_overlaps/check_missing_visual_elements had
                # no reason to flag it). All four dimensions must be set
                # together whenever a placeholder's inherited geometry is
                # touched at all.
                body_placeholder.left = b_left
                body_placeholder.top = b_top
                body_placeholder.width = b_width
                body_placeholder.height = intro_height
                # Guard against a repeat of the bug this whole block's
                # comment above describes -- if a future edit here ever
                # sets only one dimension again, fail loudly at generation
                # time instead of silently shipping a shape that renders
                # as an unreadable sliver. Zero-or-negative is never a
                # legitimate size for a real, visible shape.
                if body_placeholder.width <= 0 or body_placeholder.height <= 0:
                    raise ValueError(
                        "internal error: body placeholder ended up with a "
                        f"non-positive size (width={body_placeholder.width}, "
                        f"height={body_placeholder.height}) while making room "
                        "for the chart -- this is a bug in add_pptx_chart, not "
                        "the caller's input."
                    )
                gap = int(slide_height * 0.03)
                new_top = b_top + intro_height + gap
                usable_bottom = slide_height - int(slide_height * sb.MARGIN_FRACTION)
                remaining = usable_bottom - new_top
                min_chart_height = int(slide_height * 0.35)
                if remaining < min_chart_height:
                    raise ValueError(
                        f"Slide {slide}'s existing body text leaves too little room "
                        f"for a chart below it -- shorten the body text, or add the "
                        f"chart to a slide whose body placeholder is empty (a "
                        f"title-only chunk)."
                    )
                top = new_top
                height = remaining

        graphic_frame = target_slide.shapes.add_chart(
            chart_xl_type, left, top, width, height, chart_data
        )
        chart = graphic_frame.chart
        if title:
            chart.has_title = True
            chart.chart_title.text_frame.text = title
        # Match the deck's own designated text color (its theme's `dk1`
        # slot -- the "text" role write_pptx's own `theme` parameter writes
        # into, see `theme.py`'s _THEME_SCHEME_COLOR_TAGS) instead of leaving python-
        # pptx's chart default (black), which is unreadable on a dark
        # theme's background -- another real, live-reproduced defect: a
        # chart's axis/legend text stayed black even after `theme=
        # "bg=...,text=F8FAFC,..."` lightened everything else on the slide.
        from lxml import etree
        from pptx.oxml.ns import qn

        theme_part = target_slide.slide_layout.slide_master.part.part_related_by(RT.THEME)
        theme_root = etree.fromstring(theme_part.blob)
        clr_scheme = theme_root.find(f".//{qn('a:clrScheme')}")
        text_color = read_scheme_color(clr_scheme, "dk1") if clr_scheme is not None else None
        if text_color:
            from pptx.dml.color import RGBColor

            chart.font.color.rgb = RGBColor.from_string(text_color)  # type: ignore[no-untyped-call]
        prs.save(str(file_path))

        state_dir = Path(self._state_dir) if self._state_dir is not None else None
        preview_path, preview_skipped_reason = render_thumbnail(file_path, state_dir)
        return {
            "path": self._scope.relative(file_path),
            "slide": slide,
            "chart_type": chart_type,
            "preview_path": preview_path,
            "preview_skipped_reason": preview_skipped_reason,
        }

    @locked_by_path
    def add_pptx_hyperlink(
        self,
        path: str,
        slide: int,
        shape_index: int | str,
        url: str,
        text: Optional[str] = None,  # noqa: UP045
    ) -> dict[str, object]:
        th.validate_hyperlink_url(url)
        prs, file_path, target_slide = self._open_slide(path, slide)
        shape = th.get_shape_at_index(target_slide, slide, shape_index)
        jump_target = th.resolve_slide_jump_target(prs, slide, url)

        if text is None:
            if jump_target is not None:
                shape.click_action.target_slide = jump_target
            else:
                shape.click_action.hyperlink.address = url
            prs.save(str(file_path))
            return {
                "path": self._scope.relative(file_path),
                "slide": slide,
                "shape_index": shape_index,
                "url": url,
                "text": None,
            }

        if not shape.has_text_frame:
            raise ValueError(
                f"add_pptx_hyperlink: shape {shape_index} on slide {slide} has no text "
                "frame -- omit `text` to hyperlink the whole shape instead."
            )
        matching_run = None
        available_texts: list[str] = []
        for paragraph in shape.text_frame.paragraphs:
            for run in paragraph.runs:
                available_texts.append(run.text)
                if run.text == text:
                    matching_run = run
                    break
            if matching_run is not None:
                break
        if matching_run is None:
            raise ValueError(
                f"add_pptx_hyperlink: no run with exact text {text!r} found in shape "
                f"{shape_index} on slide {slide} -- that shape's runs are: "
                f"{available_texts!r}. The text must match one whole run exactly; "
                "hyperlinking part of a run isn't supported."
            )
        if jump_target is not None:
            from pptx.action import ActionSetting

            # Run has no public `.click_action` the way Shape does (only
            # the external-URL-only `.hyperlink`) -- ActionSetting itself
            # is fully run-compatible (its own constructor's type union
            # already includes CT_TextCharacterProperties, a run's own
            # `rPr` element type), confirmed empirically before relying
            # on it, matching Shape.click_action's own construction
            # pattern (`ActionSetting(cNvPr, self)` there).
            ActionSetting(matching_run._r.get_or_add_rPr(), matching_run).target_slide = (  # noqa: SLF001
                jump_target
            )
        else:
            matching_run.hyperlink.address = url
        prs.save(str(file_path))
        return {
            "path": self._scope.relative(file_path),
            "slide": slide,
            "shape_index": shape_index,
            "url": url,
            "text": text,
        }
