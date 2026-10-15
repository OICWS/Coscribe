"""Tool wrappers for writing a deck, template fill and extract, and text edits."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Optional

from .toolkit import PresentationToolkit


def build_templates_tools(toolkit: PresentationToolkit) -> dict[str, Callable[..., Any]]:
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

    return {
        "write_pptx": write_pptx,
        "fill_pptx_template": fill_pptx_template,
        "extract_pptx_template": extract_pptx_template,
        "edit_pptx_text": edit_pptx_text,
    }
