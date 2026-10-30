"""Toolkit methods for writing a deck, template fill and extract, and text edits."""

from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from ..._file_locks import locked_by_path
from ..._pptx_text import replace_text
from ..._svg_slide import add_svg_slide
from ..._thumbnail import render_thumbnail
from ...pptx_templates import load_builtin_templates as _load_builtin_templates
from ...pptx_templates import load_pptx_templates as _load_pptx_templates
from ..markdown_blocks import parse_blocks
from . import slide_builders as sb
from . import toolkit_helpers as th
from .qa import (
    check_overflow,
    leftover_placeholder_warnings,
)
from .template_slides import adjust_template_content_slides
from .theme import (
    apply_cjk_font_fix,
    apply_theme,
    parse_theme_tokens,
    read_scheme_color,
)
from .toolkit_base import ToolkitBase

if TYPE_CHECKING:
    pass


# python-pptx's own bundled default template (used whenever write_pptx gets
# no template_path) is authored for the legacy 4:3 canvas (10in x 7.5in) --
# confirmed live, not assumed: a bare Presentation()'s slide_width/height
# are exactly 9144000/6858000 EMU. Real PowerPoint has defaulted to 16:9
# widescreen since Office 2013, and this is the exact EMU width Microsoft
# itself uses for that preset (13.333...in -- height stays 7.5in, unchanged
# from the 4:3 default).
_WIDESCREEN_WIDTH_EMU = 12192000

# extract_pptx_template's own id validation -- same shape as the bundled
# templates' own ids ("bold-statement", "minimal-light", ...), enforced
# here rather than left to whatever a directory name happens to be, since
# this id becomes fill_pptx_template's own template_id argument afterward.
_TEMPLATE_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,62}[a-z0-9]$")


class TemplateToolsMixin(ToolkitBase):
    @locked_by_path
    def write_pptx(
        self,
        path: str,
        content: str,
        overwrite: bool = True,
        template_path: str = "",
        theme: str = "",
    ) -> dict[str, object]:
        from pptx import Presentation
        from pptx.util import Emu

        theme_tokens = parse_theme_tokens(theme)
        file_path = self._check_writable(path, overwrite)
        if template_path:
            template_file = self._check_readable(template_path)
            prs = Presentation(str(template_file))
            required_layouts = max(sb.TITLE_AND_CONTENT_LAYOUT, sb.TITLE_ONLY_LAYOUT)
            if len(prs.slide_layouts) <= required_layouts:
                raise ValueError(
                    f"Template {template_path!r} only has {len(prs.slide_layouts)} slide "
                    f"layout(s); write_pptx needs at least {required_layouts + 1}."
                )
            sb.clear_slides(prs)
        else:
            prs = Presentation()
            original_width = prs.slide_width
            prs.slide_width = Emu(_WIDESCREEN_WIDTH_EMU)
            sb.widen_stock_layouts(prs, original_width)
            # Only the freshly-created default deck, not a user-supplied
            # template_path -- silently rewriting fonts in someone's own
            # uploaded/branded template would be an unwanted side effect,
            # see this function's `theme` docstring.
            apply_cjk_font_fix(prs)
        if theme_tokens:
            apply_theme(prs, theme_tokens)
        for chunk in sb.slide_chunks(content):
            layout_id, accent, remaining_chunk = sb.parse_layout_directive(chunk)

            if layout_id == "two-column":
                if len(prs.slide_layouts) <= sb.TWO_CONTENT_LAYOUT:
                    raise ValueError(
                        f"Template only has {len(prs.slide_layouts)} slide layout(s); "
                        f"layout: two-column needs at least {sb.TWO_CONTENT_LAYOUT + 1}."
                    )
                left_text, right_text = sb.split_two_column(remaining_chunk)
                left_blocks = parse_blocks(left_text)
                right_blocks = parse_blocks(right_text)
                left_headings = [b for b in left_blocks if b.kind == "heading"]
                title = left_headings[0].text if left_headings else ""
                left_body = [b for b in left_blocks if b.kind != "heading"]
                if any(b.kind == "table" for b in left_body) or any(
                    b.kind == "table" for b in right_blocks
                ):
                    raise ValueError(
                        "layout: two-column doesn't support tables -- use "
                        "bullets/paragraphs on each side."
                    )
                if any(b.kind == "heading" for b in right_blocks):
                    raise ValueError(
                        "layout: two-column's title must come before the '>>>' marker."
                    )
                sb.add_two_column_slide(prs, title, left_body, right_blocks)
                continue

            if layout_id == "svg":
                # Unlike the other three prefab layouts, the rest of the chunk
                # is raw SVG markup, not this module's shared markdown grammar
                # -- it must not go through parse_blocks at all.
                add_svg_slide(prs, remaining_chunk)
                continue

            blocks = parse_blocks(remaining_chunk)
            headings = [block for block in blocks if block.kind == "heading"]
            title = headings[0].text if headings else ""
            table_blocks = [block for block in blocks if block.kind == "table"]
            other_blocks = [block for block in blocks if block.kind not in ("heading", "table")]

            if layout_id == "icon-list":
                if table_blocks:
                    raise ValueError(
                        "layout: icon-list doesn't support tables -- use bullets only."
                    )
                items = sb.icon_list_items(other_blocks)
                sb.add_icon_list_slide(prs, title, items, accent)
                continue
            if layout_id == "stat-callout":
                if other_blocks or len(table_blocks) != 1:
                    raise ValueError(
                        "layout: stat-callout needs exactly one pipe-table of "
                        "stat/label rows and no other content."
                    )
                stats = sb.stats_from_table(table_blocks[0].rows)
                sb.add_stat_callout_slide(prs, title, stats, accent)
                continue

            if table_blocks and other_blocks:
                raise ValueError(
                    "A slide can have a table or bullets/paragraphs, not both -- "
                    "split it across two slides."
                )
            if table_blocks:
                self._require_single_table(table_blocks)
                sb.add_table_slide(prs, title, table_blocks[0].rows)
            else:
                sb.add_bullet_slide(prs, title, blocks)
        prs.save(str(file_path))

        overflow_warnings: list[dict[str, object]] = []
        qa_skipped_reason: str | None = None
        pdf_path = th.render_to_pdf(file_path)
        if pdf_path is None:
            qa_skipped_reason = "no office program to draw the deck, or it failed"
        else:
            try:
                overflow_warnings = check_overflow(pdf_path)
            finally:
                shutil.rmtree(pdf_path.parent, ignore_errors=True)

        state_dir = Path(self._state_dir) if self._state_dir is not None else None
        preview_path, preview_skipped_reason = render_thumbnail(file_path, state_dir)

        return {
            "path": self._scope.relative(file_path),
            "slide_count": len(prs.slides),
            "bytes_written": file_path.stat().st_size,
            "overflow_warnings": overflow_warnings,
            "placeholder_warnings": leftover_placeholder_warnings(prs),
            "qa_skipped_reason": qa_skipped_reason,
            "preview_path": preview_path,
            "preview_skipped_reason": preview_skipped_reason,
        }

    @locked_by_path
    def fill_pptx_template(
        self,
        path: str,
        template_id: str,
        content: str,
        overwrite: bool = True,
    ) -> dict[str, object]:
        """Fill content into one of coscribe's own bundled starter
        templates, keeping every one of its existing slides' own designed
        visual content (backgrounds, decorative shapes, images) exactly as
        authored -- unlike write_pptx's own template_path, which clears a
        template's slides before rebuilding from scratch. This tool only
        ever writes text into a slide's own pre-existing TITLE/BODY-type
        placeholder; it never repositions a shape.

        `content`'s `---`-separated chunk count no longer has to exactly
        equal the template's fixed slide count: the template's
        repeatable "content"-role slide(s) (every bundled template has
        exactly one design used twice -- see its own description) are
        duplicated or trimmed to match however many chunks you actually
        give, so a template scales to real content length instead of
        forcing you to trim to fit or fall back to write_pptx. The
        template's non-repeatable slides (title, closing) still need
        exactly one matching chunk each, in their fixed position (title
        first if the template has one, closing last if it has one) --
        each chunk is title + bullets/paragraphs only (no `layout:`
        directives, no tables -- write_pptx handles both).
        """
        from pptx import Presentation

        all_templates = _load_builtin_templates()
        if self._custom_templates_dir is not None:
            all_templates += _load_pptx_templates(self._custom_templates_dir)
        templates_by_id = {t.id: t for t in all_templates}
        template = templates_by_id.get(template_id)
        if template is None:
            raise ValueError(
                f"Unknown template {template_id!r}. Available: {sorted(templates_by_id)}"
            )
        file_path = self._check_writable(path, overwrite)
        prs = Presentation(str(template.path))
        # Coscribe's own bundled templates, not a user-supplied file --
        # safe (and worth doing unconditionally) to fix their empty
        # East-Asian typeface the same way write_pptx's own default deck
        # does. See `theme.py`'s _CJK_FALLBACK_TYPEFACE.
        apply_cjk_font_fix(prs)
        chunks = sb.slide_chunks(content)
        adjust_template_content_slides(prs, template.slide_roles, len(chunks))
        slides = list(prs.slides)
        for index, (slide, chunk) in enumerate(zip(slides, chunks, strict=True), start=1):
            layout_id, _accent, remaining = sb.parse_layout_directive(chunk)
            if layout_id:
                raise ValueError(
                    f"fill_pptx_template doesn't support 'layout:' directives "
                    f"(found {layout_id!r} on slide chunk {index}) -- layout: "
                    f"positions new shapes on a freshly-added slide, and this "
                    f"tool fills an existing template slide's existing "
                    f"placeholders instead. Use write_pptx for layout: <id> "
                    f"slides."
                )
            blocks = parse_blocks(remaining)
            if any(block.kind == "table" for block in blocks):
                raise ValueError(
                    f"fill_pptx_template doesn't support tables yet (slide "
                    f"chunk {index} has one) -- use write_pptx for a table "
                    f"slide."
                )
            headings = [block for block in blocks if block.kind == "heading"]
            title = headings[0].text if headings else ""
            body_blocks = [block for block in blocks if block.kind != "heading"]
            if title:
                if slide.shapes.title is None:
                    raise ValueError(
                        f"Slide {index} of template {template_id!r} has no title "
                        f"placeholder to receive chunk {index}'s heading "
                        f"{title!r} -- remove the heading or use a different "
                        f"template."
                    )
                sb.set_title(slide, title)
            if body_blocks:
                body_placeholder = sb.find_body_placeholder(slide)
                if body_placeholder is None:
                    raise ValueError(
                        f"Slide {index} of template {template_id!r} has no "
                        f"body/content placeholder to receive chunk {index}'s "
                        f"bullets or paragraphs -- remove the content or use a "
                        f"different template."
                    )
                sb.fill_content_placeholder(body_placeholder, body_blocks)
        prs.save(str(file_path))

        overflow_warnings: list[dict[str, object]] = []
        qa_skipped_reason: str | None = None
        pdf_path = th.render_to_pdf(file_path)
        if pdf_path is None:
            qa_skipped_reason = "no office program to draw the deck, or it failed"
        else:
            try:
                overflow_warnings = check_overflow(pdf_path)
            finally:
                shutil.rmtree(pdf_path.parent, ignore_errors=True)

        state_dir = Path(self._state_dir) if self._state_dir is not None else None
        preview_path, preview_skipped_reason = render_thumbnail(file_path, state_dir)

        return {
            "path": self._scope.relative(file_path),
            "template_id": template_id,
            "slide_count": len(prs.slides),
            "bytes_written": file_path.stat().st_size,
            "overflow_warnings": overflow_warnings,
            "placeholder_warnings": leftover_placeholder_warnings(prs),
            "qa_skipped_reason": qa_skipped_reason,
            "preview_path": preview_path,
            "preview_skipped_reason": preview_skipped_reason,
        }

    def extract_pptx_template(
        self,
        source_path: str,
        template_id: str,
        name: str,
        description: str,
        overwrite: bool = False,
    ) -> dict[str, object]:
        """Distill a reusable template from an existing reference deck
        (e.g. one the user just attached -- their own company's branded
        .pptx) so fill_pptx_template can reuse its exact design (theme
        colors, fonts, decorative shapes, master/layout structure) for
        new content afterward, instead of hand-rebuilding that design
        shape by shape or guessing at colors.

        Classifies the reference deck's own real slides into the same
        three roles every bundled template already uses: the first slide
        is "title", the last slide is "closing" (only if the deck has
        more than one slide), everything in between is "content" (the
        only repeatable role -- fill_pptx_template duplicates/trims it to
        fit however much content you actually give later). Every slide
        must already have a real, usable title and/or body placeholder
        (the same kind fill_pptx_template writes into) -- a slide that
        doesn't is a real limitation this reports as an error, not a
        silent skip: redesign or remove that slide in the reference deck
        first, or use write_pptx instead of a template for this deck.

        Once this returns, template_id is immediately usable as
        fill_pptx_template's own template_id argument -- no separate
        registration step.

        Args:
            source_path: path to the reference .pptx already in the workspace
            template_id: a short id for the new template (lowercase
                letters/digits/hyphens, e.g. "acme-corp") -- what
                fill_pptx_template's template_id argument refers to
                afterward
            name: a short human-readable name (e.g. "Acme Corp")
            description: one sentence describing the template's look
                (colors, mood) -- shown alongside the bundled templates'
                own descriptions wherever a template is picked
            overwrite: if a template with this id already exists, replace
                it (default False -- raises instead, since silently
                replacing a named template other calls may already
                reference is a different risk than overwriting one file)
        """
        import yaml
        from pptx import Presentation
        from pptx.opc.constants import RELATIONSHIP_TYPE as RT

        if self._custom_templates_dir is None:
            raise ValueError(
                "No custom templates directory is configured -- extract_pptx_template "
                "has nowhere to save the new template."
            )
        if not _TEMPLATE_ID_RE.match(template_id):
            raise ValueError(
                f"template_id {template_id!r} must be lowercase letters/digits/hyphens "
                f"only (e.g. 'acme-corp')."
            )
        templates_dir = Path(self._custom_templates_dir)
        template_dir = templates_dir / template_id
        if template_dir.exists() and not overwrite:
            raise FileExistsError(
                f"A template with id {template_id!r} already exists at {template_dir} -- "
                f"pass overwrite=True to replace it, or pick a different template_id."
            )

        file_path = self._check_readable(source_path)
        prs = Presentation(str(file_path))
        slide_count = len(prs.slides)
        if slide_count == 0:
            raise ValueError(f"{source_path!r} has no slides -- nothing to extract.")

        slide_roles: list[str] = []
        for index, slide in enumerate(prs.slides):
            if index == 0:
                role = "title"
            elif slide_count > 1 and index == slide_count - 1:
                role = "closing"
            else:
                role = "content"
            has_title = slide.shapes.title is not None
            has_body = sb.find_body_placeholder(slide) is not None
            if not has_title and not has_body:
                raise ValueError(
                    f"Slide {index + 1} of {source_path!r} has no usable title or "
                    f"body placeholder for fill_pptx_template to write into later -- "
                    f"extract_pptx_template needs every slide in the reference deck "
                    f"to have at least one. Redesign or remove that slide in the "
                    f"reference deck, or use write_pptx instead of a template for "
                    f"this deck."
                )
            slide_roles.append(role)

        accent = "6366F1"  # a reasonable default if the theme has no accent1 at all
        if prs.slide_masters:
            theme_part = prs.slide_masters[0].part.part_related_by(RT.THEME)
            from lxml import etree
            from pptx.oxml.ns import qn

            root = etree.fromstring(theme_part.blob)
            clr_scheme = root.find(f".//{qn('a:clrScheme')}")
            if clr_scheme is not None:
                accent = read_scheme_color(clr_scheme, "accent1") or accent

        template_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy(str(file_path), str(template_dir / "template.pptx"))
        manifest = {
            "id": template_id,
            "name": name,
            "description": description,
            "accent": accent,
            "slide_count": slide_count,
            "slide_roles": slide_roles,
        }
        (template_dir / "template.yaml").write_text(
            yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8"
        )

        return {
            "template_id": template_id,
            "name": name,
            "slide_count": slide_count,
            "slide_roles": slide_roles,
            "accent": accent,
            "saved_to": str(template_dir),
        }

    @locked_by_path
    def edit_pptx_text(
        self,
        path: str,
        slide: int,
        title: Optional[str] = None,  # noqa: UP045
        content: Optional[str] = None,  # noqa: UP045
        placeholder_index: int = 0,
        find: str = "",
        replace: str = "",
        remove: bool = False,
    ) -> dict[str, object]:
        """Edit one slide's title and/or body text, or replace a phrase
        anywhere (`find`); the rest of the file is left as authored."""
        if (title is None and content is None) == (not find):
            raise ValueError("edit_pptx_text needs title and/or content, or find, to change.")
        prs, file_path, target_slide = self._open_slide(path, slide or int(bool(find)))
        replaced = replace_text(prs, slide, find, replace, remove) if find else None
        if title is not None:
            if target_slide.shapes.title is None:
                raise ValueError(
                    f"Slide {slide} of {path!r} has no title placeholder to receive "
                    f"new title text -- read_pptx the slide first to see what's "
                    f"actually there."
                )
            sb.set_title(target_slide, title)
        if content is not None:
            blocks = parse_blocks(content)
            if any(block.kind == "table" for block in blocks):
                raise ValueError(
                    "edit_pptx_text doesn't support tables -- edit_pptx_text is "
                    "for a slide's own title/bullet placeholders only."
                )
            body_placeholder = sb.find_body_placeholder(target_slide, placeholder_index)
            if body_placeholder is None:
                raise ValueError(
                    f"Slide {slide} of {path!r} has no content placeholder at "
                    f"placeholder_index={placeholder_index} to receive new body "
                    f"text -- read_pptx the slide first to see what's actually "
                    f"there, or try a different placeholder_index."
                )
            sb.fill_content_placeholder(body_placeholder, blocks)
        prs.save(str(file_path))

        overflow_warnings: list[dict[str, object]] = []
        qa_skipped_reason: str | None = None
        pdf_path = th.render_to_pdf(file_path)
        if pdf_path is None:
            qa_skipped_reason = "no office program to draw the deck, or it failed"
        else:
            try:
                overflow_warnings = check_overflow(pdf_path)
            finally:
                shutil.rmtree(pdf_path.parent, ignore_errors=True)

        state_dir = Path(self._state_dir) if self._state_dir is not None else None
        preview_path, preview_skipped_reason = render_thumbnail(file_path, state_dir)

        return {
            "path": self._scope.relative(file_path),
            "slide": slide,
            "replaced": replaced,
            "overflow_warnings": overflow_warnings,
            "placeholder_warnings": leftover_placeholder_warnings(prs),
            "qa_skipped_reason": qa_skipped_reason,
            "preview_path": preview_path,
            "preview_skipped_reason": preview_skipped_reason,
        }
