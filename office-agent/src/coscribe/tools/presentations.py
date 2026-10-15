"""PowerPoint (.pptx) read/write tools, scoped to a single workspace root.

Mirrors ``tools/office/document_tools.py``/``office/xlsx`` -- same ``WorkspaceScope``
sandboxing, same shape (a toolkit class + a ``build_*_tools`` factory).

Unlike docx/pdf/xlsx, ``python-pptx`` (the library used here) hasn't had a
release since August 2024 -- it's the standard, complete-enough library for
this, not a "mature and audited" pick like the others. And unlike every
other tool in this package, ``write_pptx`` optionally shells out to headless
LibreOffice (``soffice``) to render the deck to PDF and flag text that
overflows its slide bounds -- the single most common visual defect,
per Anthropic's own published pptx Skill notes (see ``ARCHITECTURE.md`` for
why we don't use that Skill directly: it's script-driven, and coscribe
has no code-execution tool). This is a *diagnostic*, not a requirement --
``soffice`` missing, timing out, or failing to convert just means the write
still succeeds with ``overflow_warnings: []`` and a ``qa_skipped_reason``
explaining why.

``content`` is markdown where a line containing exactly ``---`` separates
slides (the same convention Pandoc/Marp/reveal.js already use), reusing
``office/markdown_blocks.py``'s ``parse_blocks``/``Block`` per slide chunk: the first
heading becomes the slide title, remaining blocks become the body. A slide
may have a table *or* bullets/paragraphs, not both -- deliberately
constrained, like ``write_xlsx``'s per-sheet-overwrite rule.

``pdfplumber``/``pptx`` are imported lazily, inside each function that
actually needs them, rather than at module level -- same real, measured
startup-time reasoning as ``office/docx``'s identical change, see that
module's docstring and runtime_lg/README.md's startup-time section.
``PresentationType`` is only ever used as a type annotation (never at
runtime, thanks to ``from __future__ import annotations``), so it's
imported under ``TYPE_CHECKING`` instead of even a lazy runtime import.

``add_pptx_chart`` only builds through python-pptx's high-level
``CategoryChartData``/``add_chart`` API, never hand-written chart XML --
axis/series registration is correct by construction that way. Same
deliberate scoping as ``office/xlsx``'s ``add_xlsx_chart``: single-
purpose bar/line/pie charts only, no stacked or secondary-axis/combo
charts -- exactly the configurations Anthropic's own pptx skill documents
as producing schema-valid XML that PowerPoint silently treats as corrupt.
Restricting the feature surface avoids that failure class outright rather
than needing a post-hoc validator. Chart data is a pipe-table string, the
same convention ``write_xlsx`` already uses -- not a list/dict tool
parameter, which no tool in this package uses: aisuite's Gemini schema
inference has broken on less exotic type hints than that (see the
``Optional[int]``/``Optional[str]`` comments below and in
``office/xlsx``).

``add_pptx_image``/``set_pptx_notes`` and ``write_pptx``'s/``write_docx``'s
``template_path`` are all pure high-level python-pptx/python-docx API calls,
no raw XML. ``set_pptx_transition`` and ``add_pptx_animation`` are not --
python-pptx has no transition or animation API at all, so both hand-build
OOXML via ``lxml``. ``set_pptx_transition`` is low-risk hand-written XML
(the base ECMA-376 schema has a ``<p:transition>`` element; a fresh slide's
own children are verified to always be ``['cSld', 'clrMapOvr']``, so
appending at the end is always schema-correct here). ``add_pptx_animation``
is the riskiest thing in this file: its ``<p:timing>`` tree structure and
per-effect XML (``fade``/``fly-in``) are cross-checked against
``hugohe3/ppt-master``'s shipped, PowerPoint-authored
``pptx_animation_presets.json`` rather than written from memory, and the
saved file is re-opened and structurally verified before it's allowed to
replace the user's real file -- but that verification is structural, not
visual, since this sandbox has no real PowerPoint to test against, only
LibreOffice. See ``ARCHITECTURE.md`` for the full reasoning.

Every hand-XML write in this file (``set_pptx_transition``,
``add_pptx_animation``, ``edit_pptx_theme_colors``, and the theme-blob
edits inside ``write_pptx``/``fill_pptx_template`` for ``theme=``/CJK-font
handling) also runs through ``_ooxml_validate.assert_ooxml_valid`` before
the mutated element is ever serialized into the file -- a real ECMA-376
schema check (see ``_ooxml_schemas/NOTICE.md``), not just the
application-level checks above. This catches what those checks aren't
designed to: a structurally wrong OOXML document that happens to still
satisfy a narrower "did my specific edit land" check, or that ``prs.save()``
and LibreOffice's own more forgiving parser would silently accept anyway.
"""

from __future__ import annotations

import re
import shutil
from collections.abc import Callable, Sequence
from io import BytesIO
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

from ..runtime import tool_metadata
from ._chart_data import CHART_TYPES, parse_chart_table
from ._file_locks import locked_by_path
from ._ooxml_validate import assert_ooxml_valid
from ._output_truncation import cap_read_output
from ._pptx_shapes import describe_members, in_group, set_slide_box
from ._pptx_text import replace_text
from ._svg_slide import add_svg_slide
from ._thumbnail import render_thumbnail
from ._workspace import WorkspaceScope
from .office.markdown_blocks import Block, parse_blocks
from .office.pptx import slide_builders as sb
from .office.pptx import toolkit_helpers as th
from .office.pptx.animation import (
    ANIMATIONS,
    AUDIO_CONTENT_TYPES,
    AUDIO_MARKER_SIZE_EMU,
    AUDIO_TRIGGERS,
    TRIGGERS,
    add_animation_step,
    build_audio_pic_element,
    build_audio_timing_node,
    ensure_paragraph_build,
    next_timing_id,
    register_audio_media_part_class,
    resolve_animation_preset,
    timing_root_child_list,
    verify_animation_readback,
)
from .office.pptx.effects import SHAPE_EFFECT_TYPES, apply_shape_effect
from .office.pptx.qa import (
    check_overflow,
    leftover_placeholder_warnings,
    preview_deck,
    shape_bbox,
)
from .office.pptx.shape_description import describe_shape as _describe_shape
from .office.pptx.shape_description import emu_to_inches
from .office.pptx.smartart import is_smartart, smartart_data_part
from .office.pptx.template_slides import adjust_template_content_slides, duplicate_slide_part
from .office.pptx.theme import (
    THEME_HEX_RE,
    THEME_SCHEME_SLOTS,
    apply_cjk_font_fix,
    apply_theme,
    parse_theme_color_slots,
    parse_theme_tokens,
    read_scheme_color,
    set_scheme_color,
)
from .office.pptx.transitions import (
    TRANSITIONS,
    mark_mce_ignorable,
    set_slide_transition,
)
from .office.pptx.xmlns import (
    A14_NS,
    P_NS,
)
from .pptx_templates import load_builtin_templates as _load_builtin_templates
from .pptx_templates import load_pptx_templates as _load_pptx_templates

if TYPE_CHECKING:
    from pptx.presentation import Presentation as PresentationType


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


class PresentationToolkit:
    def __init__(
        self,
        root: str | Path,
        *,
        state_dir: str | Path | None = None,
        custom_templates_dir: str | Path | None = None,
        extra_readable: Sequence[str | Path] = (),
        extra_writable: Sequence[str | Path] = (),
    ) -> None:
        self._scope = WorkspaceScope(
            root, extra_readable=extra_readable, extra_writable=extra_writable
        )
        self._state_dir = state_dir
        self._custom_templates_dir = custom_templates_dir

    def _check_readable(self, path: str) -> Path:
        file_path = self._scope.resolve(path)
        if not file_path.exists():
            raise ValueError(f"File does not exist: {path}")
        if not file_path.is_file():
            raise ValueError(f"Path is not a file: {path}")
        return file_path

    def _check_writable(self, path: str, overwrite: bool) -> Path:
        file_path = self._scope.resolve(path, write=True)
        if file_path.exists() and file_path.is_dir():
            raise ValueError(f"Path is a directory: {path}")
        if file_path.exists() and not overwrite:
            raise FileExistsError(f"File already exists: {path}")
        file_path.parent.mkdir(parents=True, exist_ok=True)
        return file_path

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
            other_blocks = [
                block for block in blocks if block.kind not in ("heading", "table")
            ]

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
            qa_skipped_reason = "LibreOffice (soffice) not found or conversion failed"
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
            qa_skipped_reason = "LibreOffice (soffice) not found or conversion failed"
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
            qa_skipped_reason = "LibreOffice (soffice) not found or conversion failed"
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

    def list_pptx_transition_types(self) -> list[str]:
        """Every `transition` name `set_pptx_transition` accepts, sorted --
        PowerPoint's real native transition gallery (48 effects) plus 8
        legacy aliases. No path/slide argument: this is a static list, the
        same regardless of which file or slide you're working on."""
        return sorted(TRANSITIONS - {"none"})

    def list_pptx_animation_types(self) -> list[str]:
        """Every `animation` name `add_pptx_animation` accepts, sorted --
        PowerPoint's real native animation gallery (203 presets, grouped
        by the `entrance_`/`emphasis_`/`exit_`/`path_` prefix) plus the 6
        legacy short aliases. No path/slide argument: this is a static
        list, the same regardless of which file or slide you're working
        on."""
        return sorted(ANIMATIONS)

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
                f"fill_color {fill_color!r} must be a 6-hex-digit color (no '#'), "
                f"e.g. '38BDF8'."
            )
        if line_color and not THEME_HEX_RE.match(line_color):
            raise ValueError(
                f"line_color {line_color!r} must be a 6-hex-digit color (no '#'), "
                f"e.g. '38BDF8'."
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

        from ._native_formula import (
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
    def replace_pptx_image(
        self, path: str, slide: int, shape_index: int | str, image_path: str
    ) -> dict[str, object]:
        """Swap an existing picture's image in place, on any already-
        existing .pptx -- position, size, and crop are all untouched
        because the picture shape itself never changes, only which image
        its `<a:blip>` points at (`Picture.image` has no setter in
        python-pptx; this is the verified real mechanism, see
        PPTX_DESIGN.md §4.2). Call `list_pptx_shapes` first to find the
        picture's `shape_index` (`is_picture: true`). Raster images only
        (PNG/JPEG/GIF/BMP/TIFF -- same formats
        `add_pptx_image` supports); not SVG."""
        image_file = self._check_readable(image_path)
        prs, file_path, target_slide = self._open_slide(path, slide)
        shape = th.get_picture_shape(target_slide, slide, shape_index)
        _image_part, r_id = shape.part.get_or_add_image_part(str(image_file))
        shape._element.blipFill.blip.rEmbed = r_id  # noqa: SLF001
        prs.save(str(file_path))

        state_dir = Path(self._state_dir) if self._state_dir is not None else None
        preview_path, preview_skipped_reason = render_thumbnail(file_path, state_dir)
        return {
            "path": self._scope.relative(file_path),
            "slide": slide,
            "shape_index": shape_index,
            "preview_path": preview_path,
            "preview_skipped_reason": preview_skipped_reason,
        }

    @locked_by_path
    def crop_pptx_image(
        self,
        path: str,
        slide: int,
        shape_index: int | str,
        crop_left: float = 0.0,
        crop_right: float = 0.0,
        crop_top: float = 0.0,
        crop_bottom: float = 0.0,
    ) -> dict[str, object]:
        """Crop an existing picture shape in place -- each `crop_*` is a
        fraction (0.0-1.0) of the image's own original width/height to
        trim from that edge; the shape's on-slide position/size are
        untouched, only which part of the image shows through inside
        that same box changes (`Picture.crop_*`, the exact mechanism
        `set_pptx_background_image` already uses for its own cover-crop
        -- native python-pptx API, no hand-built XML). Call
        `list_pptx_shapes` first to find the picture's `shape_index`
        (`is_picture: true`). Sets all four values together every call
        (not incremental) -- pass only the edges you actually want
        trimmed, the rest default to 0.0 (uncropped)."""
        if not (0.0 <= crop_left < 1.0 and 0.0 <= crop_right < 1.0):
            raise ValueError("crop_left/crop_right must each be within [0.0, 1.0).")
        if not (0.0 <= crop_top < 1.0 and 0.0 <= crop_bottom < 1.0):
            raise ValueError("crop_top/crop_bottom must each be within [0.0, 1.0).")
        if crop_left + crop_right >= 1.0:
            raise ValueError(
                f"crop_left ({crop_left}) + crop_right ({crop_right}) must be < 1.0 "
                f"-- otherwise no part of the image's width would remain visible."
            )
        if crop_top + crop_bottom >= 1.0:
            raise ValueError(
                f"crop_top ({crop_top}) + crop_bottom ({crop_bottom}) must be < 1.0 "
                f"-- otherwise no part of the image's height would remain visible."
            )
        prs, file_path, target_slide = self._open_slide(path, slide)
        shape = th.get_picture_shape(target_slide, slide, shape_index)
        shape.crop_left = crop_left
        shape.crop_right = crop_right
        shape.crop_top = crop_top
        shape.crop_bottom = crop_bottom
        prs.save(str(file_path))

        state_dir = Path(self._state_dir) if self._state_dir is not None else None
        preview_path, preview_skipped_reason = render_thumbnail(file_path, state_dir)
        return {
            "path": self._scope.relative(file_path),
            "slide": slide,
            "shape_index": shape_index,
            "crop_left": crop_left,
            "crop_right": crop_right,
            "crop_top": crop_top,
            "crop_bottom": crop_bottom,
            "preview_path": preview_path,
            "preview_skipped_reason": preview_skipped_reason,
        }

    def list_pptx_icons(self) -> list[str]:
        """Every icon name `add_pptx_icon` accepts, sorted -- a curated
        subset of Lucide (https://lucide.dev, ISC license), not the
        full ~1500-icon set. No path/slide argument: this is a static
        list, the same regardless of which file or slide you're
        working on."""
        return sorted(th.ICON_NAMES)

    @locked_by_path
    def add_pptx_icon(
        self,
        path: str,
        slide: int,
        icon_name: str,
        left_in: float = 1.0,
        top_in: float = 1.0,
        size_in: float = 1.0,
        color: str = "1F2937",
    ) -> dict[str, object]:
        """Insert a real icon (rasterized from Lucide, see
        `list_pptx_icons`) onto an existing slide, as a new square
        picture -- unlike `layout: icon-list`'s glyph-in-a-circle
        (write_pptx's own bundled shape, not a real icon), this is an
        actual recognizable pictogram. Call `list_pptx_icons()` first if
        you're not sure `icon_name` is bundled; an unknown name raises
        immediately rather than silently doing nothing."""
        if icon_name not in th.ICON_NAMES:
            raise ValueError(
                f"Unknown icon {icon_name!r} -- call list_pptx_icons() to see the "
                f"available names."
            )
        if not THEME_HEX_RE.match(color):
            raise ValueError(f"color {color!r} must be a 6-hex-digit color (no '#').")
        prs, file_path, target_slide = self._open_slide(path, slide)

        from pptx.util import Inches

        recolored = th.recolor_icon(th.ICONS_DIR / f"{icon_name}.png", color)
        buffer = BytesIO()
        recolored.save(buffer, format="PNG")
        buffer.seek(0)
        target_slide.shapes.add_picture(
            buffer, Inches(left_in), Inches(top_in), width=Inches(size_in), height=Inches(size_in)
        )
        prs.save(str(file_path))

        state_dir = Path(self._state_dir) if self._state_dir is not None else None
        preview_path, preview_skipped_reason = render_thumbnail(file_path, state_dir)
        return {
            "path": self._scope.relative(file_path),
            "slide": slide,
            "icon_name": icon_name,
            "preview_path": preview_path,
            "preview_skipped_reason": preview_skipped_reason,
        }

    @locked_by_path
    def recolor_pptx_icon(
        self, path: str, slide: int, shape_index: int | str, color: str
    ) -> dict[str, object]:
        if not THEME_HEX_RE.match(color):
            raise ValueError(f"color {color!r} must be a 6-hex-digit color (no '#').")
        prs, file_path, target_slide = self._open_slide(path, slide)
        shape = th.get_picture_shape(target_slide, slide, shape_index)

        from PIL import Image

        current_image = Image.open(BytesIO(shape.image.blob))
        recolored = th.recolor_image(current_image, color)
        buffer = BytesIO()
        recolored.save(buffer, format="PNG")
        buffer.seek(0)
        _image_part, r_id = shape.part.get_or_add_image_part(buffer)
        shape._element.blipFill.blip.rEmbed = r_id  # noqa: SLF001
        prs.save(str(file_path))

        state_dir = Path(self._state_dir) if self._state_dir is not None else None
        preview_path, preview_skipped_reason = render_thumbnail(file_path, state_dir)
        return {
            "path": self._scope.relative(file_path),
            "slide": slide,
            "shape_index": shape_index,
            "color": color.upper(),
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

    @staticmethod
    def _require_single_table(table_blocks: list[Block]) -> None:
        if len(table_blocks) > 1:
            raise ValueError("A slide can have at most one table.")

    def _open_slide(self, path: str, slide: int) -> tuple[PresentationType, Path, Any]:
        """Load `path`, validate `slide` is in range, and return (prs,
        file_path, target_slide) -- the load-validate-locate sequence every
        tool that modifies one existing slide repeats."""
        from pptx import Presentation

        file_path = self._check_readable(path)
        prs = Presentation(str(file_path))
        slide_count = len(prs.slides)
        if not 1 <= slide <= slide_count:
            raise ValueError(f"Slide {slide} out of range: deck has {slide_count} slides")
        return prs, file_path, prs.slides[slide - 1]

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
        self, path: str, slide: int, insert_at: Optional[int] = None  # noqa: UP045
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
    def add_pptx_image(
        self,
        path: str,
        slide: int,
        image_path: str,
        left: float = 1.0,
        top: float = 1.0,
        width: Optional[float] = None,  # noqa: UP045
        height: Optional[float] = None,  # noqa: UP045
    ) -> dict[str, object]:
        from pptx.util import Inches

        image_file = self._check_readable(image_path)
        prs, file_path, target_slide = self._open_slide(path, slide)

        target_slide.shapes.add_picture(
            str(image_file),
            Inches(left),
            Inches(top),
            width=Inches(width) if width is not None else None,
            height=Inches(height) if height is not None else None,
        )
        prs.save(str(file_path))

        state_dir = Path(self._state_dir) if self._state_dir is not None else None
        preview_path, preview_skipped_reason = render_thumbnail(file_path, state_dir)
        return {
            "path": self._scope.relative(file_path),
            "slide": slide,
            "preview_path": preview_path,
            "preview_skipped_reason": preview_skipped_reason,
        }

    @locked_by_path
    def set_pptx_background_image(
        self, path: str, slide: int, image_path: str
    ) -> dict[str, object]:
        """python-pptx's slide.background.fill only supports solid()/
        gradient(), no picture fill at all -- so a background image is a
        full-slide `add_picture` at (0, 0) plus two things python-pptx
        does support natively that a naive stretch-to-fill would skip:
        a CSS `background-size: cover`-style crop (via Picture.crop_*,
        computed from the image's own real aspect ratio, not the slide's)
        so the image isn't distorted, and moving the resulting <p:pic>
        element to be the first shape child of the slide's spTree (right
        after the always-present nvGrpSpPr/grpSpPr) so it renders behind
        every existing placeholder/shape -- add_picture appends at the
        end (front-most) by default, confirmed empirically before writing
        this, which is the opposite of what a background needs."""
        from PIL import Image
        from pptx.oxml.ns import qn

        image_file = self._check_readable(image_path)
        prs, file_path, target_slide = self._open_slide(path, slide)

        with Image.open(image_file) as image:
            image_width, image_height = image.size

        slide_width = prs.slide_width
        slide_height = prs.slide_height
        image_ratio = image_width / image_height
        slide_ratio = slide_width / slide_height

        crop_left = crop_right = crop_top = crop_bottom = 0.0
        if image_ratio > slide_ratio:
            # Image is relatively wider than the slide -- crop its sides.
            visible_fraction = slide_ratio / image_ratio
            crop_left = crop_right = (1 - visible_fraction) / 2
        elif image_ratio < slide_ratio:
            # Image is relatively taller than the slide -- crop top/bottom.
            visible_fraction = image_ratio / slide_ratio
            crop_top = crop_bottom = (1 - visible_fraction) / 2

        picture = target_slide.shapes.add_picture(
            str(image_file), 0, 0, width=slide_width, height=slide_height
        )
        picture.crop_left = crop_left
        picture.crop_right = crop_right
        picture.crop_top = crop_top
        picture.crop_bottom = crop_bottom

        sp_tree = target_slide.shapes._spTree
        pic_element = picture._element
        sp_tree.remove(pic_element)
        group_props = sp_tree.find(qn("p:grpSpPr"))
        insert_at = list(sp_tree).index(group_props) + 1 if group_props is not None else 0
        sp_tree.insert(insert_at, pic_element)

        prs.save(str(file_path))

        state_dir = Path(self._state_dir) if self._state_dir is not None else None
        preview_path, preview_skipped_reason = render_thumbnail(file_path, state_dir)
        return {
            "path": self._scope.relative(file_path),
            "slide": slide,
            "preview_path": preview_path,
            "preview_skipped_reason": preview_skipped_reason,
        }

    @locked_by_path
    def add_pptx_scrim(
        self, path: str, slide: int, opacity: float = 0.35, color: str = "000000"
    ) -> dict[str, object]:
        """A full-slide semi-transparent rectangle, layered above any
        background picture but below every other shape -- keeps title/body
        text legible over a busy photo background, the same "scrim" idea a
        real slide-design tool uses. `python-pptx` has no transparency API
        on `FillFormat` at all, so `<a:alpha>` is hand-appended under the
        `<a:srgbClr>` element `fill.solid()` already builds -- verified
        empirically (a real LibreOffice-rendered black rectangle at 35%
        alpha over a white slide came back mid-gray, not solid black, so
        the transparency is genuinely applied, not silently ignored)
        before writing this. Standalone rather than a `set_pptx_background_
        image` parameter, deliberately -- it composes with a review step
        that decides *whether* a slide actually needs it, rather than
        applying it unconditionally to every background image."""
        from pptx.dml.color import RGBColor
        from pptx.enum.shapes import MSO_SHAPE
        from pptx.oxml.ns import qn
        from pptx.oxml.xmlchemy import OxmlElement

        prs, file_path, target_slide = self._open_slide(path, slide)

        shape = target_slide.shapes.add_shape(
            MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height
        )
        shape.fill.solid()
        shape.fill.fore_color.rgb = RGBColor.from_string(color)  # type: ignore[no-untyped-call]
        shape.line.fill.background()
        shape.shadow.inherit = False

        srgb_clr = shape.fill._xPr.find(qn("a:solidFill")).find(qn("a:srgbClr"))
        alpha = OxmlElement("a:alpha")
        alpha.set("val", str(int(opacity * 100000)))
        srgb_clr.append(alpha)

        sp_tree = target_slide.shapes._spTree
        scrim_element = shape._element
        sp_tree.remove(scrim_element)
        existing_pics = sp_tree.findall(qn("p:pic"))
        if existing_pics:
            insert_at = list(sp_tree).index(existing_pics[-1]) + 1
        else:
            group_props = sp_tree.find(qn("p:grpSpPr"))
            insert_at = list(sp_tree).index(group_props) + 1 if group_props is not None else 0
        sp_tree.insert(insert_at, scrim_element)

        prs.save(str(file_path))

        state_dir = Path(self._state_dir) if self._state_dir is not None else None
        preview_path, preview_skipped_reason = render_thumbnail(file_path, state_dir)
        return {
            "path": self._scope.relative(file_path),
            "slide": slide,
            "preview_path": preview_path,
            "preview_skipped_reason": preview_skipped_reason,
        }

    @locked_by_path
    def add_pptx_shape_effect(
        self,
        path: str,
        slide: int,
        shape_index: int | str,
        effect: str,
        color: str = "000000",
        opacity: float = 0.4,
        size_pt: float = 8.0,
        distance_pt: float = 4.0,
        direction: float = 45.0,
    ) -> dict[str, object]:
        """Apply a drop shadow, glow, or soft edge to one shape -- any
        kind (autoshape, picture, connector), since CT_EffectList (the
        `<p:spPr>` child that carries these) is shared by all of them.
        python-pptx has no public API for this at all -- its own
        ShadowFormat can only suppress an inherited theme shadow
        (`shape.shadow.inherit = False`, used by add_pptx_scrim above),
        never create or customize one -- so every effect element this
        writes is hand-built against the real ECMA-376 schema
        (`_ooxml_schemas/transitional/dml-main.xsd`'s CT_EffectList/
        CT_GlowEffect/CT_OuterShadowEffect/CT_SoftEdgesEffect).

        Deliberately narrower than the full schema, matching
        set_pptx_transition/add_pptx_animation's own precedent -- only
        the two color-bearing effects real slide design actually reaches
        for (shadow, glow) and one color-free effect (soft_edge) are
        supported; blur/fillOverlay/innerShdw/prstShdw/reflection are
        not."""
        if effect not in SHAPE_EFFECT_TYPES:
            raise ValueError(f"effect {effect!r} must be one of {sorted(SHAPE_EFFECT_TYPES)}.")
        if effect != "none":
            if not THEME_HEX_RE.match(color):
                raise ValueError(f"color {color!r} must be a 6-hex-digit color (no '#').")
            if not 0.0 <= opacity <= 1.0:
                raise ValueError(f"opacity {opacity} must be between 0.0 and 1.0.")
            if size_pt <= 0:
                raise ValueError(f"size_pt {size_pt} must be positive.")
            if effect == "shadow" and distance_pt < 0:
                raise ValueError(f"distance_pt {distance_pt} must be non-negative.")

        prs, file_path, target_slide = self._open_slide(path, slide)
        shape = th.get_shape_at_index(target_slide, slide, shape_index)
        apply_shape_effect(shape, effect, color.upper(), opacity, size_pt, distance_pt, direction)
        assert_ooxml_valid(target_slide.element, "add_pptx_shape_effect")
        prs.save(str(file_path))

        state_dir = Path(self._state_dir) if self._state_dir is not None else None
        preview_path, preview_skipped_reason = render_thumbnail(file_path, state_dir)
        return {
            "path": self._scope.relative(file_path),
            "slide": slide,
            "shape_index": shape_index,
            "effect": effect,
            "preview_path": preview_path,
            "preview_skipped_reason": preview_skipped_reason,
        }

    @locked_by_path
    def read_pptx_xml(
        self, path: str, slide: int, shape_index: int | str, part: str = "auto"
    ) -> dict[str, object]:
        """Raw OOXML for one shape -- the escape hatch for anything
        python-pptx has no API for at all beyond what add_pptx_shape_effect/
        add_pptx_animation/set_pptx_transition already hand-write (see this
        file's own module docstring): editing SmartArt node text, or
        inspecting/tweaking any other element this package's own tools
        don't wrap. Always read before calling edit_pptx_xml -- the real
        element names/namespaces/nesting are what xpath there has to
        target, and this is the only way to see them."""
        from lxml import etree

        th.validate_xml_part_arg(part)
        _prs, _file_path, target_slide = self._open_slide(path, slide)
        shape = th.get_shape_at_index(target_slide, slide, shape_index)
        use_smartart_data = part == "smartart_data" or (part == "auto" and is_smartart(shape))
        if use_smartart_data:
            root = etree.fromstring(smartart_data_part(shape).blob)
            source = "smartart_data"
        else:
            root = shape._element  # noqa: SLF001
            source = "shape"
        return {
            "xml": etree.tostring(root, pretty_print=True, encoding="unicode"),
            "source": source,
        }

    @locked_by_path
    def edit_pptx_xml(
        self,
        path: str,
        slide: int,
        shape_index: int | str,
        xpath: str,
        new_text: Optional[str] = None,  # noqa: UP045
        set_attributes: Optional[str] = None,  # noqa: UP045
        part: str = "auto",
    ) -> dict[str, object]:
        """Edit one element inside a shape's raw OOXML, found by XPath --
        the narrow, bounded escape hatch ROADMAP.md's own "Later" backlog
        named: element-scoped (an xpath must resolve to exactly one real
        element, same "unique match or raise" discipline edit_file's own
        old_text uses), not an unrestricted whole-file patch -- there's no
        way to add/remove/reorder elements here, only change an existing
        one's text or attributes. Reach for this only when no dedicated
        tool already covers what's needed; it's real hand-XML, no
        argument-level guardrails beyond "the result must still be
        well-formed"."""
        from lxml import etree

        if new_text is None and not set_attributes:
            raise ValueError("Provide new_text and/or set_attributes -- nothing to change.")
        th.validate_xml_part_arg(part)
        parsed_attributes = th.parse_set_attributes(set_attributes)

        prs, file_path, target_slide = self._open_slide(path, slide)
        shape = th.get_shape_at_index(target_slide, slide, shape_index)
        use_smartart_data = part == "smartart_data" or (part == "auto" and is_smartart(shape))

        # Real gotcha, verified empirically (not assumed): `//foo` in
        # XPath means "search the whole document this node belongs to",
        # not "search this node's own descendants" -- calling
        # `.xpath("//dgm:t")` directly on `shape._element` (which lives
        # inside the full <p:sld> tree, alongside every *other* shape on
        # the slide) would silently match content in a sibling shape too,
        # breaking the "exactly one match" contract in a way that could
        # edit the wrong shape without ever raising. Parsing a standalone
        # copy of just this shape's own serialized XML sidesteps the
        # whole problem -- `//` on a detached tree can only ever reach
        # that tree's own content, no cross-shape leakage possible. The
        # SmartArt data part is already parsed this same way below
        # (a fresh `etree.fromstring(data_part.blob)`, its own document),
        # so this makes both sources behave identically.
        data_part = None
        original_shape_element = None
        if use_smartart_data:
            data_part = smartart_data_part(shape)
            root = etree.fromstring(data_part.blob)
            source = "smartart_data"
        else:
            original_shape_element = shape._element  # noqa: SLF001
            root = etree.fromstring(etree.tostring(original_shape_element))
            source = "shape"

        matches = root.xpath(xpath, namespaces=th.GENERIC_XML_NSMAP)
        if len(matches) != 1:
            raise ValueError(
                f"xpath {xpath!r} matched {len(matches)} element(s) inside this {source} "
                "XML -- must match exactly one. Call read_pptx_xml first to see the real "
                "structure and narrow the xpath."
            )
        element = matches[0]
        if not isinstance(element, etree._Element):  # noqa: SLF001
            raise ValueError(
                f"xpath {xpath!r} matched an attribute or text value, not an element -- "
                "target the element itself (e.g. '//dgm:t' not '//dgm:t/@type')."
            )

        if new_text is not None:
            element.text = new_text
        for name, value in parsed_attributes.items():
            element.set(th.resolve_xml_qname(name), value)

        # Splice the edited detached copy back into the real, live slide
        # tree at the shape's own original position (getparent().replace,
        # not append -- this preserves shape order, since a slide's
        # z-order is its shapes' own document order). Then validate the
        # *whole slide* via assert_ooxml_valid, same "never serialize an
        # unvalidated write" guarantee every other hand-XML tool in this
        # file makes (the ECMA-376 Transitional/pml.xsd this file already
        # vendors) -- catches a mistake in this edit even if it's
        # syntactically well-formed (e.g. a required child now missing).
        # A SmartArt data part's own <dgm:dataModel> root has no vendored
        # schema here (a genuinely separate schema this codebase hasn't
        # needed until now) -- well-formedness (the etree.tostring below
        # already guarantees that much, or it would have raised) is the
        # only check available for that source, documented honestly
        # rather than silently claiming a stronger guarantee than this
        # tool actually gives.
        if source == "shape":
            assert original_shape_element is not None  # narrows for mypy
            original_shape_element.getparent().replace(original_shape_element, root)
            assert_ooxml_valid(target_slide.element, "edit_pptx_xml")
        else:
            assert data_part is not None  # narrows for mypy -- true whenever source != "shape"
            data_part.blob = etree.tostring(
                root, xml_declaration=True, encoding="UTF-8", standalone=True
            )
        prs.save(str(file_path))

        return {
            "path": self._scope.relative(file_path),
            "slide": slide,
            "shape_index": shape_index,
            "source": source,
        }

    @locked_by_path
    def set_pptx_notes(self, path: str, slide: int, notes: str) -> dict[str, object]:
        prs, file_path, target_slide = self._open_slide(path, slide)
        target_slide.notes_slide.notes_text_frame.text = notes
        prs.save(str(file_path))
        return {"path": self._scope.relative(file_path), "slide": slide}

    @locked_by_path
    def set_pptx_transition(
        self, path: str, slide: int, transition: str, duration: float = 1.0
    ) -> dict[str, object]:
        if transition not in TRANSITIONS:
            raise ValueError(
                f"Unknown transition {transition!r}. Use one of: "
                f"{', '.join(sorted(TRANSITIONS))}"
            )
        prs, file_path, target_slide = self._open_slide(path, slide)
        set_slide_transition(target_slide.element, transition, duration)
        assert_ooxml_valid(target_slide.element, "set_pptx_transition")
        prs.save(str(file_path))
        return {"path": self._scope.relative(file_path), "slide": slide, "transition": transition}

    @locked_by_path
    def add_pptx_animation(
        self,
        path: str,
        slide: int,
        shape_index: int | str,
        animation: str,
        duration: float = 0.5,
        trigger: str = "on-click",
        delay: float = 0.0,
        by_paragraph: bool = False,
    ) -> dict[str, object]:
        if animation not in ANIMATIONS:
            raise ValueError(
                f"Unknown animation {animation!r}. Use one of: {', '.join(sorted(ANIMATIONS))}"
            )
        if trigger not in TRIGGERS:
            raise ValueError(
                f"Unknown trigger {trigger!r}. Use one of: {', '.join(sorted(TRIGGERS))}"
            )
        prs, file_path, target_slide = self._open_slide(path, slide)
        shape = th.get_shape_at_index(target_slide, slide, shape_index)
        if in_group(shape):
            raise ValueError(
                f"Shape {shape_index!r} is inside a group, and PowerPoint animates a group as one "
                "shape: animate the group (the path before the last '/') instead."
            )
        shape_id = shape.shape_id
        duration_ms = max(1, round(duration * 1000))
        delay_ms = max(0, round(delay * 1000))

        paragraph_indexes: list[int] | None = None
        if by_paragraph:
            if not shape.has_text_frame:
                raise ValueError(
                    f"add_pptx_animation: shape {shape_index} on slide {slide} has no text "
                    "frame -- by_paragraph needs a shape with text."
                )
            paragraph_indexes = [
                index
                for index, paragraph in enumerate(shape.text_frame.paragraphs)
                if paragraph.text.strip()
            ]
            if not paragraph_indexes:
                raise ValueError(
                    f"add_pptx_animation: shape {shape_index} on slide {slide} has no "
                    "non-empty paragraphs to animate by_paragraph."
                )
            for paragraph_index in paragraph_indexes:
                add_animation_step(
                    target_slide.element, shape_id, animation, duration_ms, trigger, delay_ms,
                    paragraph_index,
                )
            timing = target_slide.element.find(f"{{{P_NS}}}timing")
            ensure_paragraph_build(timing, shape_id)
        else:
            add_animation_step(
                target_slide.element, shape_id, animation, duration_ms, trigger, delay_ms, None
            )

        assert_ooxml_valid(target_slide.element, "add_pptx_animation")

        # Save to a temp file and verify before touching the real file --
        # if the read-back check fails, the user's file is left untouched
        # rather than silently left in a possibly-broken state.
        tmp_path = file_path.with_name(f"{file_path.name}.animation-tmp")
        prs.save(str(tmp_path))
        try:
            verify_animation_readback(
                tmp_path, slide, shape_id, animation, trigger, paragraph_indexes
            )
        except Exception:
            tmp_path.unlink(missing_ok=True)
            raise
        tmp_path.replace(file_path)

        preset = resolve_animation_preset(animation)
        actual_duration_ms = (
            duration_ms
            if preset["duration_scalable"] and preset["default_duration_ms"] is not None
            else preset["default_duration_ms"]
        )
        return {
            "path": self._scope.relative(file_path),
            "slide": slide,
            "shape_index": shape_index,
            "animation": animation,
            "trigger": trigger,
            "by_paragraph": by_paragraph,
            "paragraph_count": len(paragraph_indexes) if paragraph_indexes is not None else None,
            "duration_ms": actual_duration_ms,
        }

    @locked_by_path
    def add_pptx_audio(
        self,
        path: str,
        slide: int,
        audio_path: str,
        left_in: float = 0.3,
        top_in: float = 0.3,
        trigger: str = "auto",
        start_delay: float = 0.0,
        hidden: bool = False,
    ) -> dict[str, object]:
        if trigger not in AUDIO_TRIGGERS:
            raise ValueError(
                f"Unknown trigger {trigger!r}. Use one of: {', '.join(sorted(AUDIO_TRIGGERS))}"
            )
        audio_file = self._check_readable(audio_path)
        ext = audio_file.suffix.lower()
        if ext not in AUDIO_CONTENT_TYPES:
            raise ValueError(
                f"add_pptx_audio: unsupported audio format {ext!r} on {audio_path!r} -- "
                f"use one of: {', '.join(sorted(AUDIO_CONTENT_TYPES))}"
            )
        prs, file_path, target_slide = self._open_slide(path, slide)

        import io

        from lxml import etree
        from pptx.media import SPEAKER_IMAGE_BYTES, Video
        from pptx.opc.constants import RELATIONSHIP_TYPE as RT
        from pptx.oxml import parse_xml
        from pptx.util import Inches

        # `Video` is python-pptx's own generic media-blob wrapper (used
        # internally by `add_movie`) -- nothing in it is video-specific,
        # confirmed by reading its source before reusing it here. Its own
        # `get_or_add_media_part`/`relate_to`/`get_or_add_image_part` are
        # the same real relationship-writing plumbing `add_movie` uses,
        # reused directly rather than hand-rolled, EXCEPT for the actual
        # audio relationship type: `add_movie`'s own higher-level
        # `get_or_add_video_media_part` hardcodes `RT.VIDEO` for the
        # legacy relationship, which would be semantically wrong for
        # audio (and mismatched against this method's own `<a:audioFile>`
        # element) -- built directly with the real `RT.AUDIO` type
        # instead, confirmed to exist in python-pptx's own constants.
        register_audio_media_part_class()
        video = Video.from_path_or_file_like(str(audio_file), AUDIO_CONTENT_TYPES[ext])
        slide_part = target_slide.part
        media_part = slide_part.package.get_or_add_media_part(video)
        audio_rid = slide_part.relate_to(media_part, RT.AUDIO)
        media_rid = slide_part.relate_to(media_part, RT.MEDIA)
        # The default "media loudspeaker" icon python-pptx already bundles
        # for `add_movie`'s own poster-frame fallback -- reused as-is
        # rather than vendoring hugohe3/ppt-master's own separate icon,
        # since coscribe already ships python-pptx as a real dependency.
        _, poster_rid = slide_part.get_or_add_image_part(io.BytesIO(SPEAKER_IMAGE_BYTES))

        shape_id = target_slide.shapes._next_shape_id
        shape_name = audio_file.name
        if hidden:
            x_emu = y_emu = -AUDIO_MARKER_SIZE_EMU
        else:
            x_emu, y_emu = int(Inches(left_in)), int(Inches(top_in))

        pic = build_audio_pic_element(
            shape_id,
            shape_name,
            audio_rid,
            media_rid,
            poster_rid,
            x_emu,
            y_emu,
            AUDIO_MARKER_SIZE_EMU,
        )
        # `build_audio_pic_element` returns a plain lxml element -- python-
        # pptx's own shape factory (invoked whenever `target_slide.shapes`
        # is iterated, which `render_pptx_preview`/`list_pptx_shapes` and
        # this method's own shape_index computation below all do) expects
        # its custom `CT_Picture` subclass instead, keyed off a parser
        # python-pptx registers globally -- round-tripping through
        # `parse_xml(etree.tostring(...))` re-parses with that same
        # parser, confirmed empirically to yield the real `CT_Picture`
        # class regardless of the (arbitrary, auto-generated) namespace
        # prefixes `etree.tostring` emits for Clark-notation tags.
        target_slide.shapes._spTree.append(parse_xml(etree.tostring(pic)))
        shape_index = len(list(target_slide.shapes)) - 1

        root_child = timing_root_child_list(target_slide.element)
        timing = target_slide.element.find(f"{{{P_NS}}}timing")
        next_id = next_timing_id(timing)
        start_delay_ms = None if trigger == "on-click" else max(0, round(start_delay * 1000))
        root_child.append(build_audio_timing_node(shape_id, next_id, start_delay_ms))

        assert_ooxml_valid(target_slide.element, "add_pptx_audio")
        prs.save(str(file_path))

        return {
            "path": self._scope.relative(file_path),
            "slide": slide,
            "shape_index": shape_index,
            "trigger": trigger,
            "start_delay": (None if start_delay_ms is None else round(start_delay_ms / 1000, 3)),
            "hidden": hidden,
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

    @locked_by_path
    def check_pptx_delivery(self, path: str) -> dict[str, object]:
        import zipfile
        from collections import Counter

        file_path = self._check_readable(path)

        with zipfile.ZipFile(file_path) as archive:
            infos = [info for info in archive.infolist() if not info.is_dir()]
            name_counts = Counter(info.filename for info in infos)
            duplicate_parts = sorted(name for name, count in name_counts.items() if count > 1)
            try:
                corrupt_member = archive.testzip()
            except (NotImplementedError, RuntimeError) as exc:
                corrupt_member = f"<unreadable: {exc}>"
            media_infos = [info for info in infos if info.filename.startswith("ppt/media/")]
            media_total_bytes = sum(info.file_size for info in media_infos)
            media_largest = [
                {"part": info.filename, "bytes": info.file_size}
                for info in sorted(media_infos, key=lambda info: info.file_size, reverse=True)[
                    :5
                ]
            ]

        try:
            pptx_report = th.analyze_pptx_delivery(file_path)
        except Exception as exc:
            # A file broken enough that python-pptx itself can't fully
            # load/walk it (corrupt beyond just a duplicate/oversized
            # part -- python-pptx parses slide parts lazily, so this can
            # surface anywhere in th.analyze_pptx_delivery, not only at
            # Presentation() construction) must still return whatever
            # the raw-zip pass above already found, rather than crashing
            # this read-only audit outright -- hit for real against a
            # deliberately-corrupted test fixture, not a hypothetical.
            advisories: list[str] = []
            if corrupt_member:
                advisories.append(f"ZIP integrity failed at {corrupt_member!r}.")
            if duplicate_parts:
                advisories.append(f"Duplicate package parts: {', '.join(duplicate_parts)}.")
            advisories.append(
                f"Could not fully analyze this file as a presentation "
                f"({type(exc).__name__}: {exc}) -- only the raw package-level checks "
                "below could run."
            )
            return {
                "path": self._scope.relative(file_path),
                "zip_integrity": "corrupt" if corrupt_member else "ok",
                "corrupt_member": corrupt_member,
                "duplicate_parts": duplicate_parts,
                "slide_count": None,
                "hidden_slides": None,
                "fonts": None,
                "media": {
                    "count": len(media_infos),
                    "total_bytes": media_total_bytes,
                    "largest": media_largest,
                },
                "motion": None,
                "advisories": advisories,
            }

        advisories = []
        if corrupt_member:
            advisories.append(f"ZIP integrity failed at {corrupt_member!r}.")
        if duplicate_parts:
            advisories.append(f"Duplicate package parts: {', '.join(duplicate_parts)}.")
        if pptx_report["hidden_slides"]:
            advisories.append(
                f"{len(pptx_report['hidden_slides'])} hidden slide(s) won't show "
                f"during a normal slideshow: {pptx_report['hidden_slides']}."
            )
        if pptx_report["unsafe_fonts"]:
            advisories.append(
                f"Font(s) not on the common cross-platform-safe list: "
                f"{', '.join(pptx_report['unsafe_fonts'])} -- may substitute or render "
                "differently on a machine that doesn't have them installed."
            )
        if media_total_bytes > th.DELIVERY_MEDIA_ADVISORY_BYTES:
            advisories.append(
                f"Embedded media totals {media_total_bytes / 1_000_000:.1f}MB across "
                f"{len(media_infos)} file(s) -- consider compressing images before "
                "sending, especially by email."
            )

        return {
            "path": self._scope.relative(file_path),
            "zip_integrity": "corrupt" if corrupt_member else "ok",
            "corrupt_member": corrupt_member,
            "duplicate_parts": duplicate_parts,
            "slide_count": pptx_report["slide_count"],
            "hidden_slides": pptx_report["hidden_slides"],
            "fonts": {"used": pptx_report["fonts_used"], "unsafe": pptx_report["unsafe_fonts"]},
            "media": {
                "count": len(media_infos),
                "total_bytes": media_total_bytes,
                "largest": media_largest,
            },
            "motion": pptx_report["motion"],
            "advisories": advisories,
        }

    @locked_by_path
    def read_pptx_theme_colors(self, path: str) -> dict[str, object]:
        from lxml import etree
        from pptx import Presentation
        from pptx.opc.constants import RELATIONSHIP_TYPE as RT
        from pptx.oxml.ns import qn

        file_path = self._check_readable(path)
        prs = Presentation(str(file_path))
        master = prs.slide_masters[0]
        theme_part = master.part.part_related_by(RT.THEME)
        root = etree.fromstring(theme_part.blob)
        clr_scheme = root.find(f".//{qn('a:clrScheme')}")
        colors: dict[str, object] = dict.fromkeys(THEME_SCHEME_SLOTS)
        if clr_scheme is not None:
            for slot in THEME_SCHEME_SLOTS:
                colors[slot] = read_scheme_color(clr_scheme, slot)
        return {"path": self._scope.relative(file_path), "colors": colors}

    @locked_by_path
    def edit_pptx_theme_colors(self, path: str, colors: str) -> dict[str, object]:
        from lxml import etree
        from pptx import Presentation
        from pptx.opc.constants import RELATIONSHIP_TYPE as RT
        from pptx.oxml.ns import qn

        tokens = parse_theme_color_slots(colors)
        file_path = self._check_readable(path)
        prs = Presentation(str(file_path))
        for master in prs.slide_masters:
            theme_part = master.part.part_related_by(RT.THEME)
            root = etree.fromstring(theme_part.blob)
            clr_scheme = root.find(f".//{qn('a:clrScheme')}")
            if clr_scheme is None:
                continue
            for slot, hex_value in tokens.items():
                set_scheme_color(clr_scheme, slot, hex_value)
            assert_ooxml_valid(root, "edit_pptx_theme_colors")
            theme_part._blob = etree.tostring(  # noqa: SLF001
                root, xml_declaration=True, encoding="UTF-8", standalone=True
            )
        prs.save(str(file_path))
        return {"path": self._scope.relative(file_path), "colors": tokens}

    @locked_by_path
    def read_pptx(self, path: str, slide: Optional[int] = None) -> str:  # noqa: UP045
        from pptx import Presentation

        file_path = self._check_readable(path)
        prs = Presentation(str(file_path))
        slide_count = len(prs.slides)
        if slide is not None:
            if not 1 <= slide <= slide_count:
                raise ValueError(f"Slide {slide} out of range: deck has {slide_count} slides")
            return self._render_slide(prs.slides[slide - 1])
        return "\n\n---\n\n".join(
            self._render_slide(s, with_heading=True) for s in prs.slides
        )

    @locked_by_path
    def render_pptx_preview(self, path: str, max_slides: int = 8) -> dict[str, object]:
        file_path = self._check_readable(path)
        state_dir = Path(self._state_dir) if self._state_dir is not None else None
        return preview_deck(file_path, state_dir, max_slides)

    @staticmethod
    def _render_slide(slide: Any, with_heading: bool = False) -> str:
        title_shape = slide.shapes.title
        title = title_shape.text if title_shape is not None else ""
        title_shape_id = title_shape.shape_id if title_shape is not None else None
        lines = [f"## {title}"] if with_heading else []
        for shape in th.leaf_shapes(slide.shapes):
            if title_shape_id is not None and shape.shape_id == title_shape_id:
                continue
            if shape.has_table:
                for row in shape.table.rows:
                    lines.append("| " + " | ".join(cell.text for cell in row.cells) + " |")
            elif shape.has_text_frame:
                for paragraph in shape.text_frame.paragraphs:
                    if paragraph.text:
                        lines.append(f"- {paragraph.text}")
        return "\n".join(lines)


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
