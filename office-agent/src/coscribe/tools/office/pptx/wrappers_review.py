"""Tool wrappers for reading, previewing, delivery checks and theme colours."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Optional

from ..._output_truncation import cap_read_output
from .toolkit import PresentationToolkit


def build_review_tools(toolkit: PresentationToolkit) -> dict[str, Callable[..., Any]]:
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

        A deck built from SVG pages is drawn from them; any other deck needs
        Microsoft Office or WPS -- when neither is there, or drawing fails,
        `preview_paths` comes back empty and `preview_skipped_reason` says
        why; this is never an error.

        Pass the returned `preview_paths_csv` straight through as
        review_work's `preview_name` argument to have the reviewer look at
        every rendered slide in one call.

        Three more fields need no rendering at all, so they're always
        populated regardless of the drawing: `text_overlap_warnings`
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
        an office program, and are empty without one):
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

    return {
        "read_pptx": read_pptx,
        "render_pptx_preview": render_pptx_preview,
        "check_pptx_delivery": check_pptx_delivery,
        "read_pptx_theme_colors": read_pptx_theme_colors,
        "edit_pptx_theme_colors": edit_pptx_theme_colors,
    }
