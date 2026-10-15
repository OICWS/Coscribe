"""The deck tools as plain functions over one toolkit, with the descriptions the model reads."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any, Optional

from ....runtime import tool_metadata
from ..._output_truncation import cap_read_output
from .toolkit import PresentationToolkit


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

    # `Optional[int]`, not `int | None`: aisuite's Tools.__infer_from_signature
    # only unwraps typing.Optional (checks `get_origin(t) is Union`), and PEP
    # 604 `X | None` has origin `types.UnionType` instead -- it slips through
    # unwrapped and gets serialized as the literal string "int | None" for
    # the "type" field, which Gemini's strict OpenAPI-subset schema rejects.
    def read_pptx(path: str, slide: Optional[int] = None) -> str:  # noqa: UP045
        """Read a PowerPoint (.pptx) file under the workspace as markdown.

        Without `slide`, every slide is rendered as a `## <title>` heading
        (empty if the slide has none) followed by its bullets/table, joined
        by `---` -- a full deck overview in one call. With `slide` (1-based),
        only that slide is rendered -- use this to avoid spending context on
        slides you don't need in a large deck.

        Args:
            path: file to read, relative to the workspace root
            slide: 1-based slide number to read; omit to read every slide
        """
        return cap_read_output(
            toolkit.read_pptx(path=path, slide=slide),
            "read one slide at a time with the slide argument",
        )

    def render_pptx_preview(path: str, max_slides: int = 8) -> dict[str, object]:
        """Render every slide of a PowerPoint file to an image so you (or
        review_work) can actually look at the rendered result, not just its
        text content. Call this after building/editing a deck with
        run_node_script, which -- unlike write_pptx -- returns no
        preview_path of its own; read_pptx alone can't catch a plain,
        undesigned slide, since bullet text reads the same whether or not
        the slide behind it looks good.

        Needs LibreOffice (`soffice`)
        installed -- when it is missing, or conversion fails,
        `preview_paths` comes back empty and `preview_skipped_reason` says
        why; this is never an error.

        Pass the returned `preview_paths_csv` straight through as
        review_work's `preview_name` argument to have the reviewer look at
        every rendered slide in one call.

        Three more fields need no rendering at all, so they're always
        populated regardless of LibreOffice: `text_overlap_warnings`
        flags pairs of text boxes on the same slide whose bounding boxes
        significantly overlap (a real, reproduced defect -- a subtitle box
        landing on top of the body text), `slides_missing_visual_elements`
        lists 1-based slide numbers with no picture/chart/table/colored
        shape at all, just plain text -- a slide's background color alone
        doesn't count -- and `low_contrast_warnings` flags text whose own
        color falls below WCAG's minimum contrast ratio against its
        resolved background (computed directly from the known colors, not
        a rendered pixel check -- so it only catches text/background pairs
        with an explicit solid color on both sides; text on a photo or a
        gradient needs the existing scrim guidance and a human/review_work
        look instead). All three are objective checks, not a design
        opinion: treat any hit as something to actually fix (move the
        overlapping box, add a shape/icon/image to a flagged slide, darken/
        lighten the text or its background) before calling the deck done,
        the same way you'd react to overflow_warnings.

        Two more are measured on the rendered slides (so they need
        LibreOffice, and are empty without it):
        `small_text_slides` lists slides whose body text renders under
        14pt (`body_text_pt`) -- raise the size, or cut the words, until
        it reads from across a room -- and `sparse_slides` lists content
        slides whose text/chart/picture stops in their upper half
        (`content_ends_at_pct`): the lower half is empty, so enlarge the
        text, add the chart/table/picture that belongs there, or merge the
        slide into a neighbour. A title or closing slide may be sparse on
        purpose; a content slide may not.

        Args:
            path: the .pptx file to render, relative to the workspace root
            max_slides: cap on how many slides to render (default 8) -- a
                large deck's every slide isn't worth the token cost of
                reviewing each one
        """
        return toolkit.render_pptx_preview(path=path, max_slides=max_slides)

    def write_pptx(
        path: str,
        content: str,
        overwrite: bool = True,
        template_path: str = "",
        theme: str = "",
    ) -> dict[str, object]:
        """Create a PowerPoint (.pptx) file under the workspace from structured text.

        `content` is markdown where a line containing exactly `---` on its
        own separates slides. Within each slide: the first `#`/`##`/`###`
        heading becomes the slide title; `-`/`*` bullets and plain
        paragraphs become the slide body. A slide may have a `| a | b |`
        pipe-table instead of bullets, but not both -- put a table on its
        own slide. This is whole-file overwrite, same contract as
        write_docx/write_pdf.

        Good slide design (apply when writing `content`): short titles,
        one idea per slide, left-align body text (never centered), no
        decorative accent lines/bars under titles. If text overflows its
        slide, the response's `overflow_warnings` will say so (when
        LibreOffice is installed) -- shorten the content or split the slide
        and call write_pptx again.

        The response's `preview_path` (when LibreOffice is installed) names
        a rendered thumbnail of the first slide the user can see in the
        chat UI -- not something to fetch or parse yourself.

        With no `template_path`, the deck is real 16:9 widescreen (13.33in
        x 7.5in) -- python-pptx's own bare-default canvas is the legacy 4:3
        shape, which this corrects to what every modern PowerPoint deck
        actually uses. Chinese/Japanese/Korean text always renders in a
        real CJK typeface (Microsoft YaHei), not whatever fallback font
        the opening machine happens to pick.

        `template_path`, if given, is an existing .pptx file (e.g. one with
        the user's own branding/theme) to build the new deck on: its theme,
        fonts, and colors carry over, and its own slides are removed before
        the new ones from `content` are added. The template needs at least
        the standard "Title and Content" and "Title Only" layouts; a
        template missing those raises a clear error rather than a
        confusing one deep inside slide creation.

        `theme`, if given, gives a from-scratch deck (no `template_path`
        needed) a cohesive background/color/typography identity instead of
        the plain-white default -- comma-separated `key=value` tokens:
        `bg` (slide background), `text` (body/title text color), `surface`
        (a secondary background tone, e.g. for cards), `accent` (the
        color layout: icon-list/stat-callout slides use when they don't
        specify their own accent hex, plus hyperlinks), `heading_font`,
        `body_font`. Colors are 6-hex-digit, no `#`. Every key is
        optional. Example: `"bg=0F172A,text=F8FAFC,accent=38BDF8,
        heading_font=Georgia"` for a dark navy deck with a cyan accent.
        Applies to the whole deck (every slide, including ones added via
        `layout:` directives), not per-slide.

        `heading_font`/`body_font` pick which font PowerPoint itself
        renders with -- this tool's own `overflow_warnings` is only as
        accurate as that. Arial/Calibri/Cambria/Times New Roman/Courier
        New/Bookman Old Style/Century Schoolbook render true-to-width in
        both the overflow check *and* real Office (every common Office
        install has them, or a metric-compatible stand-in); anything else
        (Georgia, Trebuchet MS, Impact, Arial Black, Garamond, Consolas,
        Palatino Linotype -- and never Aptos, unreliable on old and new
        Office installs alike) renders correctly in real PowerPoint but
        makes `overflow_warnings` itself approximate, since whatever
        machine LibreOffice runs on for this check may substitute a
        different-width font for it -- size that font's own text
        containers with ~10% extra slack rather than trusting a clean
        overflow check at face value.

        Args:
            path: file to write, relative to the workspace root
            content: deck content in the slide-separated markdown described above
            overwrite: whether to replace the file if it already exists
            template_path: optional .pptx file to use as the deck's starting
                theme/template, relative to the workspace root
            theme: optional comma-separated color/font tokens giving a
                freeform deck a cohesive identity -- see above
        """
        return toolkit.write_pptx(
            path=path,
            content=content,
            overwrite=overwrite,
            template_path=template_path,
            theme=theme,
        )

    def fill_pptx_template(
        path: str, template_id: str, content: str, overwrite: bool = True
    ) -> dict[str, object]:
        """Create a PowerPoint (.pptx) file by filling content into one of
        coscribe's own bundled starter templates -- unlike write_pptx's
        template_path, which discards a template's own slide content and
        keeps only its theme/fonts, this keeps every one of the template's
        existing slides' actual designed visuals (backgrounds, decorative
        shapes, images) exactly as authored, and only writes your text into
        that slide's own title/body placeholder.

        Reach for this instead of write_pptx when the user wants a deck
        that looks like one of coscribe's own pre-designed templates, not
        one generated from scratch -- call load_skill("PPTX Slides") first
        to see the available template ids and each one's exact slide-by-
        slide shape.

        `content` uses the same `---`-separated-chunk convention as
        write_pptx. The chunk count no longer has to exactly match the
        template's fixed slide count: its repeatable content-slide design
        is duplicated or trimmed to fit however many chunks you give it,
        so a template scales to real content length. Its non-repeatable
        slides (title, closing) still need exactly one chunk each, in
        their fixed position (title first, closing last). Each chunk is
        title (first heading) + bullets/paragraphs only -- no `layout:
        <id>` directives and no tables (write_pptx handles both of
        those).

        Args:
            path: file to write, relative to the workspace root
            template_id: id of a bundled template (see load_skill("PPTX Slides"))
            content: deck content in the slide-separated markdown described above
            overwrite: whether to replace the file if it already exists
        """
        return toolkit.fill_pptx_template(
            path=path, template_id=template_id, content=content, overwrite=overwrite
        )

    def extract_pptx_template(
        source_path: str,
        template_id: str,
        name: str,
        description: str,
        overwrite: bool = False,
    ) -> dict[str, object]:
        """Distill a reusable template from an existing reference deck --
        e.g. one the user just attached (their own company's branded
        .pptx) -- so fill_pptx_template can reuse its exact design (theme
        colors, fonts, decorative shapes, master/layout structure) for
        new content afterward, instead of hand-rebuilding that design
        shape by shape or guessing at colors from a description.

        Classifies the reference deck's own real slides into the same
        three roles every bundled template already uses: the first slide
        is "title", the last slide is "closing" (only if the deck has
        more than one slide), everything in between is "content" (the
        only repeatable role). Every slide must already have a real,
        usable title and/or body placeholder -- a slide that doesn't
        raises a clear error naming which slide, rather than silently
        skipping it; redesign or remove that slide in the reference
        deck, or use write_pptx instead of a template for this deck.

        Once this returns, template_id is immediately usable as
        fill_pptx_template's own template_id argument in the same turn --
        no separate registration step, and it persists across future
        conversations too (it's saved alongside the bundled templates,
        just in your own local templates directory).

        Args:
            source_path: path to the reference .pptx already in the workspace
            template_id: a short id for the new template (lowercase
                letters/digits/hyphens, e.g. "acme-corp")
            name: a short human-readable name (e.g. "Acme Corp")
            description: one sentence describing the template's look
                (colors, mood)
            overwrite: if a template with this id already exists, replace
                it. Defaults to False -- raises instead.
        """
        return toolkit.extract_pptx_template(
            source_path=source_path,
            template_id=template_id,
            name=name,
            description=description,
            overwrite=overwrite,
        )

    def edit_pptx_text(
        path: str,
        slide: int,
        title: Optional[str] = None,  # noqa: UP045
        content: Optional[str] = None,  # noqa: UP045
        placeholder_index: int = 0,
        find: str = "",
        replace: str = "",
        remove: bool = False,
    ) -> dict[str, object]:
        """Change what an existing slide *says*, without touching how it
        looks, in any .pptx in the workspace (the user's own, a deck someone
        sent, one built from pages): one slide's title and/or one content
        placeholder's text, or with `find` every occurrence of a phrase in
        any shape (text boxes, group members, table cells) on one slide or
        on all, each keeping its font, size and colour. The theme, images and
        other shapes stay as they were. read_pptx(path, slide) first shows
        what a slide says.

        Args:
            path: path to an existing .pptx already in the workspace
            slide: 1-based slide index to edit; with `find`, 0 for every slide
            title: new title text, completely replacing the slide's
                existing title. Omit to leave the title untouched. Raises
                if this slide has no title placeholder at all.
            content: new body text (markdown bullets/paragraphs -- same
                convention as write_pptx, but no tables and no `layout:`
                directives), completely replacing one content
                placeholder's existing text. Omit to leave all content
                placeholders on this slide untouched.
            placeholder_index: which content placeholder `content` targets,
                0-based; leave it at 0 unless the slide has a "two column"
                layout and you also change its second area (call again
                with placeholder_index=1).
            find: exact text to replace (instead of title/content), as
                read_pptx shows it; the result lists where it was
            replace: the one-line text `find` becomes; remove: true deletes it
        """
        return toolkit.edit_pptx_text(
            path=path, slide=slide, title=title, content=content,
            placeholder_index=placeholder_index, find=find, replace=replace, remove=remove,
        )

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

    def replace_pptx_image(
        path: str, slide: int, shape_index: str, image_path: str
    ) -> dict[str, object]:
        """Swap an existing picture's image in place on an existing
        PowerPoint (.pptx) file's slide -- position, size, and crop are
        all kept exactly as they were, only the image itself changes.
        The tool for replacing a photo/icon already placed in a real
        uploaded deck (or one coscribe already generated) with a
        different one, without touching its placement.

        Call list_pptx_shapes(path, slide) first to find the picture's
        shape_index (is_picture: true).

        Args:
            path: path to an existing .pptx already in the workspace
            slide: 1-based slide index the picture is on
            shape_index: list_pptx_shapes's index, a member's path, or a name
            image_path: path to the new image file already on disk,
                relative to the workspace root. Raster formats only
                (PNG/JPEG/GIF/BMP/TIFF, same as add_pptx_image) -- not SVG.
        """
        return toolkit.replace_pptx_image(
            path=path, slide=slide, shape_index=shape_index, image_path=image_path
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

    def crop_pptx_image(
        path: str,
        slide: int,
        shape_index: str,
        crop_left: float = 0.0,
        crop_right: float = 0.0,
        crop_top: float = 0.0,
        crop_bottom: float = 0.0,
    ) -> dict[str, object]:
        """Crop an existing picture shape on an existing PowerPoint
        (.pptx) file's slide, in place -- the shape's on-slide position/
        size are untouched, only which part of the image shows through
        inside that same box changes.

        Call list_pptx_shapes(path, slide) first to find the picture's
        shape_index (is_picture: true).

        Args:
            path: path to an existing .pptx already in the workspace
            slide: 1-based slide index the picture is on
            shape_index: list_pptx_shapes's index, a member's path, or a name
            crop_left: fraction (0.0-1.0) of the image's own width to trim
                from its left edge. Defaults to 0.0 (no crop).
            crop_right: fraction (0.0-1.0) of the image's own width to trim
                from its right edge. Defaults to 0.0 (no crop).
            crop_top: fraction (0.0-1.0) of the image's own height to trim
                from its top edge. Defaults to 0.0 (no crop).
            crop_bottom: fraction (0.0-1.0) of the image's own height to
                trim from its bottom edge. Defaults to 0.0 (no crop).
        """
        return toolkit.crop_pptx_image(
            path=path,
            slide=slide,
            shape_index=shape_index,
            crop_left=crop_left,
            crop_right=crop_right,
            crop_top=crop_top,
            crop_bottom=crop_bottom,
        )

    def list_pptx_icons() -> list[str]:
        """List every icon name add_pptx_icon accepts -- a curated
        subset of Lucide (https://lucide.dev, ISC license), not its
        full ~1500-icon set. No arguments: this is a static list, not
        specific to any file."""
        return toolkit.list_pptx_icons()

    def add_pptx_icon(
        path: str,
        slide: int,
        icon_name: str,
        left_in: float = 1.0,
        top_in: float = 1.0,
        size_in: float = 1.0,
        color: str = "1F2937",
    ) -> dict[str, object]:
        """Insert a real icon onto an existing slide in a PowerPoint
        (.pptx) file, as a new square picture -- unlike write_pptx's
        `layout: icon-list` (a glyph inside a plain colored circle),
        this is an actual recognizable pictogram (rasterized from
        Lucide). Use this to add a real icon to a slide you're editing,
        or alongside other shapes on a freshly-built one.

        Call list_pptx_icons() first if you're not sure icon_name is
        bundled -- an unknown name raises immediately.

        Args:
            path: path to an existing .pptx already in the workspace
            slide: 1-based slide index to add the icon to
            icon_name: one of list_pptx_icons()'s names, e.g. "check",
                "trending-up", "lightbulb"
            left_in: horizontal position in inches from the slide's left edge
            top_in: vertical position in inches from the slide's top edge
            size_in: width and height in inches (icons are square)
            color: 6-hex-digit fill color, no '#' (default a dark
                slate gray, "1F2937")
        """
        return toolkit.add_pptx_icon(
            path=path,
            slide=slide,
            icon_name=icon_name,
            left_in=left_in,
            top_in=top_in,
            size_in=size_in,
            color=color,
        )

    def recolor_pptx_icon(
        path: str, slide: int, shape_index: str, color: str
    ) -> dict[str, object]:
        """Change the color of an icon or logo-like picture already on a
        slide, in place -- position, size, and crop are untouched, only
        the pixels change (same relationship-swap mechanism as
        `replace_pptx_image`).

        Works by re-coloring the shape's own *current* image from its
        existing alpha (transparency) channel, not by re-fetching a
        bundled icon by name -- so it recolors any icon `add_pptx_icon`
        placed (regardless of which one), and will also work on any
        other transparent-background picture with a real silhouette.
        It does **not** detect edges or shapes: every pixel that isn't
        already transparent becomes the new solid color. Using it on an
        opaque photo (no real transparency) will flatten the whole
        picture to one solid color block -- only use this on icons,
        logos, or other transparent-background pictograms.

        Call `list_pptx_shapes` first to find `shape_index`
        (`is_picture: true`).

        Args:
            path: file to modify, relative to the workspace root
            slide: 1-based slide number the icon is on
            shape_index: list_pptx_shapes's index, a member's path, or a name
            color: new 6-hex-digit fill color, no '#'
        """
        return toolkit.recolor_pptx_icon(
            path=path, slide=slide, shape_index=shape_index, color=color
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

        The response's `preview_path` (when LibreOffice is installed) names
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

    def add_pptx_image(
        path: str,
        slide: int,
        image_path: str,
        left: float = 1.0,
        top: float = 1.0,
        width: Optional[float] = None,  # noqa: UP045
        height: Optional[float] = None,  # noqa: UP045
    ) -> dict[str, object]:
        """Add a picture to an existing slide in a PowerPoint (.pptx) file.

        `image_path` must be a readable image file already on disk (e.g. one
        the user attached, or one generated by another tool). Position and
        size are in inches; `width`/`height` default to the image's native
        aspect ratio scaled from whichever one is given, or the image's
        actual size if neither is given (python-pptx's own default).

        Args:
            path: presentation file to modify, relative to the workspace root
            slide: 1-based slide number to add the image to
            image_path: image file to insert, relative to the workspace root
            left: distance from the slide's left edge, in inches
            top: distance from the slide's top edge, in inches
            width: image width in inches; omit to keep the native aspect ratio
            height: image height in inches; omit to keep the native aspect ratio
        """
        return toolkit.add_pptx_image(
            path=path,
            slide=slide,
            image_path=image_path,
            left=left,
            top=top,
            width=width,
            height=height,
        )

    def set_pptx_background_image(path: str, slide: int, image_path: str) -> dict[str, object]:
        """Set a full-bleed background image on one slide in a PowerPoint
        (.pptx) file, behind its existing title/content/other shapes.

        The image is cropped (not stretched) to cover the whole slide
        without distortion, the same way CSS `background-size: cover`
        works -- picked automatically from the image's own aspect ratio,
        nothing to configure. Use search_images + download_image first to
        find and fetch a candidate image, or point at one already in the
        workspace. Images sourced via search_images are NOT filtered by
        license -- treat a deck built with one as a draft, and say so if
        the user seems to be about to send or publish it, rather than
        silently treating the image as clear to use externally.

        Args:
            path: presentation file to modify, relative to the workspace root
            slide: 1-based slide number to set the background on
            image_path: image file to use, relative to the workspace root
        """
        return toolkit.set_pptx_background_image(path=path, slide=slide, image_path=image_path)

    def add_pptx_scrim(
        path: str, slide: int, opacity: float = 0.35, color: str = "000000"
    ) -> dict[str, object]:
        """Add a full-slide semi-transparent color layer to one slide in a
        PowerPoint (.pptx) file, between its background image (if any) and
        its other shapes -- keeps title/body text legible over a busy
        photo background instead of leaving it low-contrast.

        Not applied automatically by set_pptx_background_image -- add it
        only when text actually needs it (e.g. review_work flags a
        legibility problem after you set a background image), not as a
        blanket default on every background -- an unnecessary scrim reads
        as decorative filler the same way an unnecessary accent bar does.

        Pick `color` to contrast with the slide's actual text color, not
        its own default of black -- a dark scrim under dark title text
        barely helps (verified: still low-contrast against a busy photo);
        a light scrim (e.g. "FFFFFF") under dark text washes the photo out
        enough to read clearly while staying recognizable.

        Args:
            path: presentation file to modify, relative to the workspace root
            slide: 1-based slide number to add the scrim to
            opacity: 0.0 (fully transparent) to 1.0 (fully opaque); 0.35 is
                a reasonable starting point for dark text/light overlay or
                vice versa
            color: hex RGB color, no leading "#", e.g. "000000" for a dark
                scrim (light text over it) or "FFFFFF" for a light scrim
                (dark text over it)
        """
        return toolkit.add_pptx_scrim(path=path, slide=slide, opacity=opacity, color=color)

    def add_pptx_shape_effect(
        path: str,
        slide: int,
        shape_index: str,
        effect: str,
        color: str = "000000",
        opacity: float = 0.4,
        size_pt: float = 8.0,
        distance_pt: float = 4.0,
        direction: float = 45.0,
    ) -> dict[str, object]:
        """Apply a drop shadow, glow, or soft edge to one shape (any kind --
        autoshape, picture, connector) on a slide in a PowerPoint (.pptx)
        file.

        Calling this again with a *different* `effect` on the same shape
        adds that effect alongside whatever it already has (e.g. shadow,
        then soft_edge, leaves both). Calling it again with the *same*
        `effect` replaces that effect's own settings in place.
        `effect="none"` removes every effect this tool manages from the
        shape (color/opacity/size_pt/distance_pt/direction are ignored in
        that case).

        Args:
            path: presentation file to modify, relative to the workspace root
            slide: 1-based slide number the shape is on
            shape_index: which shape on that slide -- call list_pptx_shapes
                first to find it
            effect: "shadow", "glow", "soft_edge", or "none" to clear
            color: hex RGB color, no leading "#" -- shadow/glow only,
                ignored for soft_edge/none
            opacity: 0.0 (fully transparent) to 1.0 (fully opaque) --
                shadow/glow only
            size_pt: blur radius in points (shadow), glow radius (glow), or
                softening radius (soft_edge)
            distance_pt: how far the shadow is offset from the shape --
                shadow only, ignored otherwise
            direction: shadow offset direction in degrees, 0 = right,
                90 = down, increasing clockwise (PowerPoint's own angle
                convention) -- shadow only, ignored otherwise
        """
        return toolkit.add_pptx_shape_effect(
            path=path,
            slide=slide,
            shape_index=shape_index,
            effect=effect,
            color=color,
            opacity=opacity,
            size_pt=size_pt,
            distance_pt=distance_pt,
            direction=direction,
        )

    def read_pptx_xml(
        path: str, slide: int, shape_index: str, part: str = "auto"
    ) -> dict[str, object]:
        """Read one shape's raw underlying OOXML from a PowerPoint (.pptx)
        file -- the escape hatch for anything not covered by a dedicated
        tool (list_pptx_shapes/edit_pptx_shape and friends), most notably
        the real text inside an *existing* SmartArt diagram: python-pptx
        has no SmartArt API at all, and SmartArt's own real text doesn't
        even live in the slide's own XML -- it's in a separate linked
        part this tool resolves automatically (`part="auto"`, the
        default). Always call this before edit_pptx_xml on a shape you
        haven't inspected yet -- its own `xpath` argument has to target
        real element names/namespaces/nesting you can only see here.

        Args:
            path: presentation file to read, relative to the workspace root
            slide: 1-based slide number the shape is on
            shape_index: which shape on that slide -- call list_pptx_shapes
                first to find it (is_smartart there flags a SmartArt one)
            part: "auto" (default) reads a SmartArt shape's linked data
                part (where its real text lives) or a normal shape's own
                inline XML, whichever applies. "shape" always reads the
                shape's own inline slide XML, even for SmartArt (its
                `<p:graphicFrame>` wrapper -- position/size/relationship
                pointers, not the diagram's own content). "smartart_data"
                always reads the linked data part, and raises if this
                shape isn't SmartArt.
        """
        return toolkit.read_pptx_xml(path=path, slide=slide, shape_index=shape_index, part=part)

    def edit_pptx_xml(
        path: str,
        slide: int,
        shape_index: str,
        xpath: str,
        new_text: Optional[str] = None,  # noqa: UP045
        set_attributes: Optional[str] = None,  # noqa: UP045
        part: str = "auto",
    ) -> dict[str, object]:
        """Edit one element inside a shape's raw OOXML in a PowerPoint
        (.pptx) file, found by XPath -- the narrow escape hatch for
        anything no dedicated tool covers (most notably: changing the
        text of an *existing* node inside a SmartArt diagram, which
        python-pptx has no API for at all). Call read_pptx_xml first --
        `xpath` has to target the real structure it shows you, not a
        guess.

        Deliberately bounded, not a general patch tool: `xpath` must
        match exactly one real element (raises otherwise, same "ambiguous
        match" discipline edit_file's own old_text uses) -- there's no
        way to add, remove, or reorder elements, only change an existing
        one's text and/or attributes. `xpath` understands these
        namespace prefixes: p (presentationml), a (drawingml), r
        (relationships), dgm (SmartArt diagram), p14/a14/p15/p159
        (PowerPoint extension namespaces) -- e.g. `//dgm:t` finds every
        SmartArt text-node element, `//dgm:t[../../@modelId='1']` narrows
        to the one belonging to a specific node.

        Validated before saving -- a "shape"-part edit is checked against
        the real ECMA-376 schema (same guarantee every other hand-XML
        tool in this package already makes: an invalid result means the
        file was never touched). A "smartart_data" edit only gets a
        well-formedness check -- this package has no vendored schema for
        SmartArt's own diagram markup, so a structurally-wrong-but-still-
        well-formed edit there (e.g. a broken node relationship) won't be
        caught here; keep such edits to changing existing text content,
        not restructuring the diagram.

        Args:
            path: presentation file to modify, relative to the workspace root
            slide: 1-based slide number the shape is on
            shape_index: which shape on that slide -- call list_pptx_shapes
                first to find it
            xpath: an XPath expression that must match exactly one element
                inside the target XML (see `part`) -- call read_pptx_xml
                first to see the real structure
            new_text: if given, replaces the matched element's own direct
                text content
            set_attributes: if given, sets attributes on the matched
                element -- one "name=value" pair per line (not a
                structured object: this codebase's tool schemas have to
                stay Gemini-compatible, and a dict-typed parameter breaks
                that, same reason edit_file_batch's own `edits` is a
                delimited string too). `name` is "attr" or "prefix:attr"
                using the same namespace prefixes `xpath` understands --
                e.g. "modelId=2\ntype=parTrans" sets two plain attributes,
                "r:id=rId5" sets one in the relationships namespace
            part: which XML to search -- see read_pptx_xml's own `part`
                argument for the exact "auto"/"shape"/"smartart_data"
                meaning, identical here
        """
        return toolkit.edit_pptx_xml(
            path=path,
            slide=slide,
            shape_index=shape_index,
            xpath=xpath,
            new_text=new_text,
            set_attributes=set_attributes,
            part=part,
        )

    def set_pptx_notes(path: str, slide: int, notes: str) -> dict[str, object]:
        """Set the speaker notes for one slide in a PowerPoint (.pptx) file.

        Replaces that slide's notes entirely (not an append).

        Args:
            path: file to modify, relative to the workspace root
            slide: 1-based slide number to set notes on
            notes: the full speaker-notes text for that slide
        """
        return toolkit.set_pptx_notes(path=path, slide=slide, notes=notes)

    def set_pptx_transition(
        path: str, slide: int, transition: str, duration: float = 1.0
    ) -> dict[str, object]:
        """Set the slide-change transition for one slide in a PowerPoint (.pptx) file.

        `transition` is any of PowerPoint's own real native transitions --
        call `list_pptx_transition_types()` for the full list (48 effects
        across PowerPoint's own Subtle/Exciting/Dynamic Content gallery
        categories -- "fade"/"push"/"wipe"/"morph"/"vortex"/"honeycomb"/
        "cube"/"page_curl", etc. -- plus a few legacy aliases), or "none".
        Each effect uses PowerPoint's own sensible default variant (e.g.
        "push" always enters from the right) -- no direction/shape/style
        customization yet. `duration` is in seconds and controls how long
        the transition animation takes when advancing *into* this slide.

        Args:
            path: file to modify, relative to the workspace root
            slide: 1-based slide number to set the transition on
            transition: any name from list_pptx_transition_types(), or "none"
            duration: transition length in seconds
        """
        return toolkit.set_pptx_transition(
            path=path, slide=slide, transition=transition, duration=duration
        )

    def list_pptx_transition_types() -> list[str]:
        """List every `transition` name `set_pptx_transition` accepts --
        PowerPoint's own real native transition gallery (48 effects) plus
        8 legacy aliases. No arguments: this is a static list, not
        specific to any file."""
        return toolkit.list_pptx_transition_types()

    def list_pptx_animation_types() -> list[str]:
        """List every `animation` name `add_pptx_animation` accepts --
        PowerPoint's own real native animation gallery (203 presets across
        entrance/emphasis/exit/motion-path categories) plus 6 legacy
        aliases. No arguments: this is a static list, not specific to any
        file."""
        return toolkit.list_pptx_animation_types()

    def add_pptx_animation(
        path: str,
        slide: int,
        shape_index: str,
        animation: str,
        duration: float = 0.5,
        trigger: str = "on-click",
        delay: float = 0.0,
        by_paragraph: bool = False,
    ) -> dict[str, object]:
        """Add an animation to one shape on a slide.

        `shape_index` is 0-based, in the order shapes were added to the
        slide (the same convention `list_pptx_shapes`/`edit_pptx_shape`/
        `replace_pptx_image` use -- call `list_pptx_shapes` first to find
        it rather than guessing): for a slide from `write_pptx`, index 0
        is the title and index 1 is the body content/table; each later
        `add_pptx_image` or `add_pptx_chart` call on that slide appends
        one more shape after those.

        `animation` is any of PowerPoint's own 203 real animation
        presets -- call `list_pptx_animation_types()` for the full list,
        grouped by category (`"entrance_*"`: shape starts hidden, then
        reveals; `"exit_*"`: shape is visible, then hides; `"emphasis_*"`:
        shape stays visible throughout; `"path_*"`: shape moves along a
        motion path, then stays at the end position). The original six
        short names this tool exposed before the full catalog still work
        as aliases: `"fade"`->`"entrance_fade"`, `"fly-in"`->
        `"entrance_fly"`, `"exit-fade"`->`"exit_fade"`, `"exit-fly"`->
        `"exit_fly"`, `"emphasis-grow"`->`"emphasis_grow_shrink"`,
        `"emphasis-spin"`->`"emphasis_spin"`. A handful of presets (instant
        appear/disappear toggles, discrete state changes like changing a
        shape's font) aren't duration-adjustable in real PowerPoint either
        -- for those, `duration` is ignored and the result's own
        `duration_ms` reports what was actually used instead of silently
        pretending the requested value took effect.

        `trigger` is PowerPoint's own Animation Pane "Start" setting for
        this animation:
        - `"on-click"` (default): plays the next time the presenter
          advances past this slide -- one click, one animation. Calling
          this again with `trigger="on-click"` adds one more independent
          click group, played in the order you called them in.
        - `"with-previous"`: plays at the same time as whatever animation
          you most recently added to this slide, no extra click needed.
        - `"after-previous"`: plays automatically right when that
          previous animation finishes, no extra click needed -- use this
          to chain a sequence that auto-plays once the presenter clicks
          into the slide (the first animation in the chain can itself be
          `"after-previous"`; it just starts on slide entry, same as real
          PowerPoint). `delay` adds an extra gap (seconds) on top of
          whichever trigger you chose, e.g. a short pause between
          with-previous elements or between one after-previous step and
          the next.

        `by_paragraph=True` animates each of the shape's non-empty text
        paragraphs as its own step instead of animating the whole shape
        at once -- the standard way to reveal a bulleted list one bullet
        at a time. Combine with `trigger="on-click"` for one click per
        bullet, or `trigger="after-previous"` (with a small `delay`) to
        have the bullets cascade in automatically. Raises if the shape
        has no text frame or no non-empty paragraphs.

        This writes hand-built animation XML (python-pptx itself has no
        animation API) and is verified after saving to structurally match
        what was requested, but has only been tested against LibreOffice
        in this environment, not real PowerPoint -- treat it as best-
        effort, and have the user confirm it looks right in PowerPoint
        before relying on it for anything important. The by_paragraph
        paragraph-range targeting in particular is a standard, common
        ECMA-376 pattern but -- unlike the six base effects above -- has
        not been cross-checked against a captured real-PowerPoint sample.

        Args:
            path: file to modify, relative to the workspace root
            slide: 1-based slide number the shape is on
            shape_index: list_pptx_shapes's index, a member's path, or a name
            animation: one of list_pptx_animation_types()'s names, or one
                of the six legacy short aliases above
            duration: animation length in seconds (ignored for the few
                presets that aren't duration-adjustable -- see result's
                own duration_ms)
            trigger: "on-click", "with-previous", or "after-previous"
            delay: extra gap in seconds before this animation starts, on
                top of its trigger's own natural timing
            by_paragraph: animate each non-empty paragraph in the shape's
                text frame as its own step, instead of the whole shape
        """
        return toolkit.add_pptx_animation(
            path=path,
            slide=slide,
            shape_index=shape_index,
            animation=animation,
            duration=duration,
            trigger=trigger,
            delay=delay,
            by_paragraph=by_paragraph,
        )

    def add_pptx_audio(
        path: str,
        slide: int,
        audio_path: str,
        left_in: float = 0.3,
        top_in: float = 0.3,
        trigger: str = "auto",
        start_delay: float = 0.0,
        hidden: bool = False,
    ) -> dict[str, object]:
        """Embed an audio file (mp3/m4a/wav) on a slide -- background
        music, a voiceover/narration track, or a sound effect -- as a
        real PowerPoint media shape with a speaker icon, not just an
        attached file.

        `trigger="auto"` (default) starts playback automatically once the
        slide begins, `start_delay` seconds later (0 by default -- no
        wait). `trigger="on-click"` instead waits for the shape's own
        speaker icon to be clicked during the slideshow, matching
        PowerPoint's own "Start: On Click" option; `start_delay` is
        ignored for this trigger. Only one audio track's timing is set up
        per call -- call this again for a second track on the same or a
        different slide.

        `hidden=True` moves the speaker icon off the visible slide canvas
        instead of placing it at `(left_in, top_in)` -- use this for
        background music/narration nobody should see or accidentally
        click, keeping `trigger="auto"` so it still plays. Leave it
        `False` (the default) for a sound effect or narration the
        presenter might want to see and re-trigger manually.

        This writes hand-built OOXML (python-pptx's own `add_movie` only
        supports video, and reusing it as-is for audio would leave the
        wrong element name and relationship type on the shape) and is
        schema-validated before saving, but has only been tested against
        LibreOffice in this environment, not real PowerPoint -- treat it
        as best-effort, and have the user confirm playback sounds right
        in PowerPoint before relying on it for anything important.

        Args:
            path: file to modify, relative to the workspace root
            slide: 1-based slide number to add the audio to
            audio_path: the audio file to embed, relative to the
                workspace root -- .mp3, .m4a, or .wav
            left_in: horizontal position of the speaker icon, in inches
                (ignored if hidden=True)
            top_in: vertical position of the speaker icon, in inches
                (ignored if hidden=True)
            trigger: "auto" or "on-click"
            start_delay: seconds after slide entry before playback starts
                (only used when trigger="auto")
            hidden: move the speaker icon off-canvas instead of placing
                it on the visible slide
        """
        return toolkit.add_pptx_audio(
            path=path,
            slide=slide,
            audio_path=audio_path,
            left_in=left_in,
            top_in=top_in,
            trigger=trigger,
            start_delay=start_delay,
            hidden=hidden,
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

    def check_pptx_delivery(path: str) -> dict[str, object]:
        """Read-only audit of a finished .pptx before sending it --
        package integrity, font portability, media footprint, hidden
        slides, and a motion summary. Doesn't render or open the file
        visually (pair with render_pptx_preview/review_work for that);
        this is about problems that only show up in the file's own
        structure.

        `zip_integrity`: `"ok"` or `"corrupt"` (with `corrupt_member`
        naming which internal part, if any, failed a raw ZIP CRC check --
        a genuinely broken file, not a cosmetic issue).
        `duplicate_parts`: internal part names that appear more than
        once in the archive (should never happen in a file this project
        's own tools produced; a real defect if it does).
        `slide_count`/`hidden_slides`: 1-based slide numbers marked
        hidden (won't show during a normal slideshow -- easy to leave
        behind by accident after duplicating/reordering slides).
        `fonts.used`/`fonts.unsafe`: every font name actually referenced
        (theme major/minor fonts plus any per-run override), and the
        subset not on a curated list of fonts that ship pre-installed on
        real Windows/Mac machines -- an unsafe font may silently
        substitute (changing line breaks/sizing) on a machine that
        doesn't have it.
        `media`: total embedded media size/count and the 5 largest files
        by byte size -- a quick way to see what's bloating the file
        before emailing it.
        `motion`: which 1-based slide numbers have a transition, a real
        object animation, or an add_pptx_audio-style audio track --
        useful to sanity-check a complex deck's own motion actually
        landed where expected.
        `advisories`: human-readable summary strings for anything above
        worth flagging; empty if nothing stood out.

        Args:
            path: file to inspect, relative to the workspace root
        """
        return toolkit.check_pptx_delivery(path=path)

    def read_pptx_theme_colors(path: str) -> dict[str, object]:
        """Read an existing .pptx file's real master theme color palette
        (its `<a:clrScheme>`) -- the same colors PowerPoint's own Design
        tab color picker edits, not any one slide's own shape colors.

        Returns all 12 real slots: `dk1`/`lt1` (the base dark/light
        pair most placeholder text and backgrounds are ultimately
        derived from), `dk2`/`lt2` (a secondary dark/light pair), `accent1`
        through `accent6`, and `hlink`/`folHlink` (hyperlink colors) --
        each a 6-hex-digit string (no `#`), or `None` if that slot is
        genuinely missing (shouldn't happen in a real, valid template).
        Call this before `edit_pptx_theme_colors` to see what's actually
        there rather than guessing which slot is "the primary blue."

        Args:
            path: file to read, relative to the workspace root
        """
        return toolkit.read_pptx_theme_colors(path=path)

    def edit_pptx_theme_colors(path: str, colors: str) -> dict[str, object]:
        """Change one or more of an existing .pptx file's real master
        theme colors in place -- the same edit PowerPoint's own Design
        tab "Customize Colors" dialog makes, not a single shape's fill.

        Because every placeholder/theme-color-referencing shape across
        every slide in the file draws from these 12 shared slots, this
        can genuinely re-color an entire already-designed deck's accent
        identity (or restyle a client's branded template) in one call --
        but for that exact reason it's also the most far-reaching edit
        in this whole tool file: call `read_pptx_theme_colors` first to
        see the current palette, and confirm with the user which slot
        (`accent1`? `dk1`?) actually corresponds to the color they mean
        before changing it, since slot names don't self-evidently map to
        "the color used in the title" without looking.

        Plain hardcoded-RGB shape fills (not created via this tool) are
        untouched -- only shapes/text that reference a theme color (via
        `theme_color`, or that inherit a template layout's own
        theme-linked placeholder styling) visibly change.

        `colors` is comma-separated `key=value` pairs naming real
        `<a:clrScheme>` slots directly (`dk1`, `lt1`, `dk2`, `lt2`,
        `accent1`-`accent6`, `hlink`, `folHlink`), each a 6-hex-digit
        color (no `#`) -- only the slots you name are changed, e.g.
        `"accent1=0F6B5C,accent2=C2410C"`.

        Args:
            path: file to modify, relative to the workspace root
            colors: comma-separated slot=hexcolor pairs, e.g.
                "accent1=0F6B5C,hlink=0F6B5C"
        """
        return toolkit.edit_pptx_theme_colors(path=path, colors=colors)

    return [
        tool_metadata(read_pptx, risk_category="READ", category="documents"),
        tool_metadata(render_pptx_preview, risk_category="READ", category="documents"),
        tool_metadata(write_pptx, risk_category="WRITE_LOCAL", category="documents"),
        tool_metadata(fill_pptx_template, risk_category="WRITE_LOCAL", category="documents"),
        tool_metadata(
            extract_pptx_template, risk_category="WRITE_LOCAL", category="documents"
        ),
        tool_metadata(edit_pptx_text, risk_category="WRITE_LOCAL", category="documents"),
        tool_metadata(delete_pptx_slide, risk_category="WRITE_LOCAL", category="documents"),
        tool_metadata(duplicate_pptx_slide, risk_category="WRITE_LOCAL", category="documents"),
        tool_metadata(reorder_pptx_slide, risk_category="WRITE_LOCAL", category="documents"),
        tool_metadata(list_pptx_shapes, risk_category="READ", category="documents"),
        tool_metadata(edit_pptx_shape, risk_category="WRITE_LOCAL", category="documents"),
        tool_metadata(delete_pptx_shape, risk_category="WRITE_LOCAL", category="documents"),
        tool_metadata(list_pptx_shape_types, risk_category="READ", category="documents"),
        tool_metadata(add_pptx_shape, risk_category="WRITE_LOCAL", category="documents"),
        tool_metadata(add_pptx_formula, risk_category="WRITE_LOCAL", category="documents"),
        tool_metadata(replace_pptx_image, risk_category="WRITE_LOCAL", category="documents"),
        tool_metadata(crop_pptx_image, risk_category="WRITE_LOCAL", category="documents"),
        tool_metadata(list_pptx_icons, risk_category="READ", category="documents"),
        tool_metadata(add_pptx_icon, risk_category="WRITE_LOCAL", category="documents"),
        tool_metadata(recolor_pptx_icon, risk_category="WRITE_LOCAL", category="documents"),
        tool_metadata(edit_pptx_table_cell, risk_category="WRITE_LOCAL", category="documents"),
        tool_metadata(merge_pptx_table_cells, risk_category="WRITE_LOCAL", category="documents"),
        tool_metadata(add_pptx_chart, risk_category="WRITE_LOCAL", category="documents"),
        tool_metadata(add_pptx_image, risk_category="WRITE_LOCAL", category="documents"),
        tool_metadata(
            set_pptx_background_image, risk_category="WRITE_LOCAL", category="documents"
        ),
        tool_metadata(add_pptx_scrim, risk_category="WRITE_LOCAL", category="documents"),
        tool_metadata(add_pptx_shape_effect, risk_category="WRITE_LOCAL", category="documents"),
        tool_metadata(read_pptx_xml, risk_category="READ", category="documents"),
        tool_metadata(edit_pptx_xml, risk_category="WRITE_LOCAL", category="documents"),
        tool_metadata(set_pptx_notes, risk_category="WRITE_LOCAL", category="documents"),
        tool_metadata(set_pptx_transition, risk_category="WRITE_LOCAL", category="documents"),
        tool_metadata(
            list_pptx_transition_types, risk_category="READ", category="documents"
        ),
        tool_metadata(add_pptx_animation, risk_category="WRITE_LOCAL", category="documents"),
        tool_metadata(
            list_pptx_animation_types, risk_category="READ", category="documents"
        ),
        tool_metadata(add_pptx_audio, risk_category="WRITE_LOCAL", category="documents"),
        tool_metadata(add_pptx_hyperlink, risk_category="WRITE_LOCAL", category="documents"),
        tool_metadata(check_pptx_delivery, risk_category="READ", category="documents"),
        tool_metadata(read_pptx_theme_colors, risk_category="READ", category="documents"),
        tool_metadata(edit_pptx_theme_colors, risk_category="WRITE_LOCAL", category="documents"),
    ]
