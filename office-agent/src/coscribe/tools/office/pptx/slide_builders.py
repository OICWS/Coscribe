"""Slide builders for write_pptx's Markdown input."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

from ..markdown_blocks import Block, parse_inline_runs

if TYPE_CHECKING:
    from pptx.presentation import Presentation as PresentationType

TITLE_AND_CONTENT_LAYOUT = 1

TITLE_ONLY_LAYOUT = 5

TWO_CONTENT_LAYOUT = 3

# write_pptx's prefab layout library (see builtin_skills/pptx/SKILL.md) --
# a slide chunk's first non-blank line, if it matches this, selects a
# pre-positioned layout instead of the default title+bullets/table shape.
# Positions for each are computed once by the layout functions below from
# the deck's own slide_width/slide_height, not re-derived per call the way
# a run_node_script pptxgenjs script has to -- this is what eliminates the
# overlap-bug class by construction rather than hoping the model's ad-hoc
# positioning math is correct every time.
LAYOUT_IDS = frozenset({"icon-list", "stat-callout", "two-column", "svg"})

LAYOUT_PREFIX_RE = re.compile(r"^layout:\s*", re.IGNORECASE)

LAYOUT_DIRECTIVE_RE = re.compile(
    r"^layout:\s*(?P<id>[a-z-]+)(?:\s+(?P<accent>[0-9A-Fa-f]{6}))?\s*$", re.IGNORECASE
)

TWO_COLUMN_MARKER_RE = re.compile(r"^>>>$")

ICON_GLYPH_RE = re.compile(r"^\[(?P<glyph>.{1,4})\]\s*(?P<text>.*)$")

# A glyph of 3+ plain ASCII letters is almost certainly a spelled-out word
# (e.g. "dash", "star", "bolt" -- observed live) rather than a symbol; a
# 1-2 letter glyph (initials like "AI") is still allowed through.
WORD_LIKE_GLYPH_RE = re.compile(r"^[A-Za-z]{3,}$")

# Plain ASCII only -- observed live, an emoji/pictograph glyph (e.g. a
# multi-color "house" or "rocket" character) renders via the font's own
# built-in color glyph, which ignores the icon circle's font.color.rgb
# override entirely. The result is a deck where some icons are clean
# accent-colored circles and others are mismatched full-color stickers,
# inconsistently, depending on which specific character the model picked --
# not something this code can control once it's an emoji glyph, so it's
# rejected up front instead of shipping an inconsistent-looking deck.
SAFE_GLYPH_RE = re.compile(r"^[A-Za-z0-9!?*+\-=/#@%&]+$")

ICON_LIST_MAX_ITEMS = 6

STAT_CALLOUT_MAX_ITEMS = 4

# Fractions of slide_width/slide_height for the body content area, measured
# against python-pptx's own default Title-and-Content layout's real
# placeholder geometry (0.5in/1.75in margins on a 10in x 7.5in slide) --
# see content_area's own docstring.
MARGIN_FRACTION = 0.05

CONTENT_TOP_FRACTION = 0.2333

CONTENT_BOTTOM_FRACTION = 0.9


def slide_chunks(content: str) -> list[str]:
    return [chunk for chunk in content.split("\n---\n") if chunk.strip()]


def clear_slides(prs: PresentationType) -> None:
    """Remove every existing slide from a loaded template, in place.

    Removing only the <p:sldId> list entry leaves the slide's XML part
    orphaned in the zip package, where it collides with a newly-added
    slide's auto-generated part name (e.g. both claiming
    'ppt/slides/slide1.xml') -- verified empirically to produce a
    'Duplicate name' warning and a genuinely corrupt-risk file on save.
    Dropping the relationship first (`drop_rel`) makes python-pptx's
    package writer omit the now-unreachable part entirely, which is the
    correct fix, also verified empirically."""
    from pptx.oxml.ns import qn

    sld_id_lst = prs.slides._sldIdLst  # noqa: SLF001
    for sld_id in list(sld_id_lst):
        r_id = sld_id.get(qn("r:id"))
        prs.part.drop_rel(r_id)
        sld_id_lst.remove(sld_id)


def widen_stock_layouts(prs: PresentationType, original_width: int) -> None:
    """After widening `prs.slide_width` (a bare `Presentation()`'s stock
    layouts are authored for the old, narrower canvas), rescale every
    TITLE/CENTER_TITLE/SUBTITLE/BODY/OBJECT-type placeholder's left/width
    proportionally to the new width -- top/height untouched, since only
    the width changed, not the height.

    A uniform horizontal scale (rather than e.g. only widening
    right-anchored placeholders) is what keeps this correct for the
    "Two Content" layout's two side-by-side OBJECT placeholders too: both
    columns and the gap between them scale by the same factor, so they
    stay equal width with a proportionally-sized gap, instead of one
    column growing and the other staying put. Verified empirically (not
    just derived): the resulting margins/gaps on every stock layout used
    by this file (Title Slide, Title and Content, Title Only, Two
    Content) render at the same *proportional* position as before, just
    scaled up -- see the write_pptx docstring and SKILL.md for the live
    render this was checked against.

    Critical detail, found live: these stock placeholders start with no
    explicit <a:xfrm> of their own at all (position/size is entirely
    inherited from the slide master) -- `placeholder.top`/`.height`
    resolve that inheritance correctly on *read*, but writing `.left`/
    `.width` makes python-pptx materialize a brand-new <a:xfrm> with
    whichever fields weren't explicitly set defaulting to 0, silently
    discarding the inherited top/height (rendered as a title clipped to
    a zero-height box). Reading top/height first and writing them back
    unchanged is what keeps them intact."""
    from pptx.enum.shapes import PP_PLACEHOLDER

    scale = prs.slide_width / original_width
    if scale == 1:
        return
    relevant = frozenset(
        {
            PP_PLACEHOLDER.TITLE,
            PP_PLACEHOLDER.CENTER_TITLE,
            PP_PLACEHOLDER.SUBTITLE,
            PP_PLACEHOLDER.BODY,
            PP_PLACEHOLDER.OBJECT,
        }
    )
    for master in prs.slide_masters:
        for layout in master.slide_layouts:
            for placeholder in layout.placeholders:
                if placeholder.placeholder_format.type in relevant:
                    top, height = placeholder.top, placeholder.height
                    placeholder.left = round(placeholder.left * scale)
                    placeholder.width = round(placeholder.width * scale)
                    placeholder.top = top
                    placeholder.height = height


def add_inline_runs(paragraph: Any, text: str) -> None:
    """pptx counterpart to ``office/docx/_xml.py``'s ``_add_inline_runs`` -- adds
    ``text`` as one run per ``parse_inline_runs`` fragment so
    ``**bold**``/``*italic*`` render as real formatting instead of literal
    markup characters."""
    for run_text, bold, italic in parse_inline_runs(text):
        run = paragraph.add_run()
        run.text = run_text
        if bold:
            run.font.bold = True
        if italic:
            run.font.italic = True


def set_title(slide: Any, title: str) -> None:
    # .clear() first -- see fill_content_placeholder's docstring for why:
    # a freshly-added slide's title placeholder is already empty, so this
    # is a no-op there, but fill_pptx_template reuses this same helper on
    # an *existing* template slide's title, which a real-world template
    # (anyone's own uploaded .pptx, not just coscribe's own bundled ones)
    # almost always ships with real placeholder/sample text already in it.
    text_frame = slide.shapes.title.text_frame
    text_frame.clear()
    add_inline_runs(text_frame.paragraphs[0], title)


def add_bullet_slide(prs: PresentationType, title: str, blocks: list[Block]) -> None:
    body_blocks = [block for block in blocks if block.kind != "heading"]
    if not body_blocks:
        # No body content -- Title Only avoids leaving an empty "click to
        # add text" placeholder in the deck.
        slide = prs.slides.add_slide(prs.slide_layouts[TITLE_ONLY_LAYOUT])
        set_title(slide, title)
        return
    slide = prs.slides.add_slide(prs.slide_layouts[TITLE_AND_CONTENT_LAYOUT])
    set_title(slide, title)
    fill_content_placeholder(slide.placeholders[1], body_blocks)


NUMERIC_CELL_RE = re.compile(r"^[¥$€]?-?[\d,]+(\.\d+)?\s*[%MKmk]?$")

PERCENT_CELL_RE = re.compile(r"^(-?\d+(?:\.\d+)?)%$")


def looks_numeric_cell(text: str) -> bool:
    """Heuristic for right-aligning a table cell's text -- ¥8.2M/34%/112%/
    2,847 all match, plain words (region/person names) don't. Used only to
    decide alignment, never to reject/transform content, so a false
    negative (a numeric-looking value rendered left-aligned) is harmless."""
    return bool(NUMERIC_CELL_RE.match(text.strip()))


def percent_cell_over_100(text: str) -> bool:
    """True for a lone "NNN%" cell over 100 -- a completion-rate/target-
    attainment table's most useful signal, and the one piece of design
    polish a real user directly flagged a competing tool doing that
    coscribe's own tables didn't (see PPTX_DESIGN.md §0)."""
    match = PERCENT_CELL_RE.match(text.strip())
    return match is not None and float(match.group(1)) > 100


def set_cell_thin_bottom_border(cell: Any, color_hex: str) -> None:
    """Hairline bottom-only border (hides left/right/top) -- the "minimal
    horizontal-rule table" look instead of PowerPoint's default full grid.
    ``CT_TableCellProperties``'s child sequence is schema-fixed (lnL, lnR,
    lnT, lnB, *then* a fill element) and python-pptx has no generated
    insert-in-order helpers for the ln* elements in this version (`dir()`
    on a real ``tcPr`` has no `_insert_lnL`/etc.) -- inserting in the
    wrong order still round-trips fine through python-pptx's own lenient
    reader (confirmed empirically), but real PowerPoint enforces the
    schema strictly, so this always locates tcPr's existing fill child
    (call ``cell.fill.background()``/``.solid()`` *before* this, never
    after) and inserts lnL/lnR/lnT/lnB immediately before it, guaranteeing
    correct order regardless of what fill was set."""
    from lxml import etree
    from pptx.oxml.ns import qn

    fill_tags = {
        qn("a:noFill"),
        qn("a:solidFill"),
        qn("a:gradFill"),
        qn("a:blipFill"),
        qn("a:pattFill"),
        qn("a:grpFill"),
    }
    tc_pr = cell._tc.get_or_add_tcPr()
    insert_at = len(tc_pr)
    for index, child in enumerate(tc_pr):
        if child.tag in fill_tags:
            insert_at = index
            break
    for offset, (tag, border_color) in enumerate(
        [("a:lnL", None), ("a:lnR", None), ("a:lnT", None), ("a:lnB", color_hex)]
    ):
        line = etree.Element(qn(tag))
        if border_color is None:
            etree.SubElement(line, qn("a:noFill"))
        else:
            line.set("w", "9525")  # 0.75pt hairline
            solid_fill = etree.SubElement(line, qn("a:solidFill"))
            etree.SubElement(solid_fill, qn("a:srgbClr")).set("val", border_color)
        tc_pr.insert(insert_at + offset, line)


def add_table_slide(prs: PresentationType, title: str, rows: list[list[str]]) -> None:
    """Real, live-reported bug this fixes (PPTX_DESIGN.md §0): building a
    table with no styling at all leaves PowerPoint's own default table
    style applied -- a dated, heavy blue-banded grid a real user directly
    compared against a competing tool's output and found worse-looking,
    despite that competitor's "table" not even being a real table object.
    Strips the default style (no fill/banding), replaces the full grid
    with hairline bottom-only rules, right-aligns numeric-looking cells,
    and bolds+flags any lone "NNN%" cell over 100 in a warm accent color --
    a completion-rate table's single most useful visual signal, and
    specifically the one polish detail a competing tool was confirmed to
    do that this function didn't.

    Real, live-reported bug this `content_area` call fixes too: the
    previous hardcoded `Inches(0.5), Inches(9)` placement was sized for
    python-pptx's own default 10in-wide blank Presentation(), but
    write_pptx always resizes the deck to widescreen
    (`_WIDESCREEN_WIDTH_EMU` in `template_tools.py`, 13.333in) -- on the real slide width the
    table actually ends up on, that fixed 9in width left ~3.8in of dead
    space on the right, visibly off-center. icon-list/stat-callout
    already computed position from the deck's own real dimensions via
    `content_area`; this did not, confirmed directly against a real
    rendered screenshot."""
    from pptx.dml.color import RGBColor
    from pptx.enum.dml import MSO_THEME_COLOR
    from pptx.enum.text import PP_ALIGN
    from pptx.util import Pt

    slide = prs.slides.add_slide(prs.slide_layouts[TITLE_ONLY_LAYOUT])
    set_title(slide, title)
    n_cols = max(len(row) for row in rows)
    left, top, width, height = content_area(prs)
    table_shape = slide.shapes.add_table(len(rows), n_cols, left, top, width, height)
    table = table_shape.table
    table.first_row = False
    table.horz_banding = False

    # theme_color, not a literal RGB -- follows whatever the deck's own
    # <a:clrScheme> dk1 is (the stock near-black default, or write_pptx's
    # `theme` token's `text` value), so a table stays readable if the
    # deck sets a dark background instead of staying hardcoded dark-gray-
    # on-white. flagged_color stays a literal: "over 100%" is a semantic
    # warning color, not part of the deck's own identity.
    flagged_color = RGBColor(0xB3, 0x26, 0x1E)  # type: ignore[no-untyped-call]
    header_border = "333333"
    body_border = "D9D9D9"

    for row_index, row in enumerate(rows):
        is_header = row_index == 0
        for col_index in range(n_cols):
            cell_text = row[col_index] if col_index < len(row) else ""
            cell = table.cell(row_index, col_index)
            cell.fill.background()
            set_cell_thin_bottom_border(cell, header_border if is_header else body_border)
            cell.margin_top = Pt(6)
            cell.margin_bottom = Pt(6)
            paragraph = cell.text_frame.paragraphs[0]
            paragraph.alignment = (
                PP_ALIGN.RIGHT if not is_header and looks_numeric_cell(cell_text) else PP_ALIGN.LEFT
            )
            add_inline_runs(paragraph, cell_text)
            flagged = not is_header and percent_cell_over_100(cell_text)
            for run in paragraph.runs:
                run.font.size = Pt(12)
                if is_header:
                    run.font.bold = True
                    run.font.color.theme_color = MSO_THEME_COLOR.DARK_1
                elif flagged:
                    run.font.bold = True
                    run.font.color.rgb = flagged_color
                else:
                    run.font.color.theme_color = MSO_THEME_COLOR.DARK_1


def parse_layout_directive(chunk: str) -> tuple[str, str, str]:
    """Split an optional ``layout: <id> [ACCENTHEX]`` directive off the
    first non-blank line of a slide chunk. Returns ``(layout_id,
    accent_hex, remaining_chunk)`` -- ``layout_id`` is ``""`` when the
    first non-blank line isn't a layout directive at all, which is the
    existing title+bullets/table path, byte-for-byte unchanged.
    ``accent_hex`` is ``""`` when no explicit hex was given -- the
    icon-list/stat-callout builders treat that as "follow the deck's
    theme accent color" rather than a hardcoded fallback hex, so a
    slide's accent tracks whatever `write_pptx`'s `theme` parameter (or
    the stock theme, if none was given) sets accent1 to. A line that
    *does* start with ``layout:`` but doesn't fully match (bad id,
    malformed hex) raises rather than silently falling through as plain
    body text, since that would be a confusing way to fail."""
    lines = chunk.splitlines()
    for index, raw_line in enumerate(lines):
        line = raw_line.strip()
        if not line:
            continue
        if not LAYOUT_PREFIX_RE.match(line):
            return "", "", chunk
        match = LAYOUT_DIRECTIVE_RE.match(line)
        if match is None:
            raise ValueError(
                f"Malformed layout directive {line!r} -- expected "
                f"'layout: <id> [ACCENTHEX]' with id one of "
                f"{', '.join(sorted(LAYOUT_IDS))} and an optional 6-hex-digit color."
            )
        layout_id = match.group("id").lower()
        if layout_id not in LAYOUT_IDS:
            raise ValueError(
                f"Unknown layout {layout_id!r} -- valid layouts are "
                f"{', '.join(sorted(LAYOUT_IDS))}."
            )
        accent = (match.group("accent") or "").upper()
        remaining = "\n".join(lines[:index] + lines[index + 1 :])
        return layout_id, accent, remaining
    return "", "", chunk


def content_area(prs: PresentationType) -> tuple[int, int, int, int]:
    """(left, top, width, height) in EMU for the body area below the title
    placeholder -- expressed as fractions of the deck's own
    slide_width/slide_height (measured against python-pptx's own default
    Title-and-Content layout's real placeholder geometry: 0.5in/1.75in
    margins on a 10in x 7.5in slide), not hardcoded inches, so it still
    holds under a differently-sized `template_path` deck, not just the
    default 4:3 canvas."""
    # `or` fallback, not an assert: python-pptx types slide_width/slide_height
    # as `Length | None` (only None for a malformed/sizeless deck, which
    # never happens for a real .pptx), and 9144000/6858000 EMU is exactly
    # python-pptx's own default 10in x 7.5in -- the same size this
    # function's constants were measured against.
    slide_width = prs.slide_width or 9144000
    slide_height = prs.slide_height or 6858000
    left = int(slide_width * MARGIN_FRACTION)
    top = int(slide_height * CONTENT_TOP_FRACTION)
    width = int(slide_width * (1 - 2 * MARGIN_FRACTION))
    height = int(slide_height * (CONTENT_BOTTOM_FRACTION - CONTENT_TOP_FRACTION))
    return left, top, width, height


def icon_list_items(blocks: list[Block]) -> list[tuple[str, str]]:
    """(glyph, label) pairs from a `layout: icon-list` slide's bullet
    blocks -- `- [X] label` uses X as the glyph, a bare bullet is
    auto-numbered."""
    if not blocks:
        raise ValueError("layout: icon-list needs at least one bullet item.")
    if any(block.kind not in ("bullet", "number") for block in blocks):
        raise ValueError("layout: icon-list only accepts bullet items -- no paragraphs or tables.")
    if len(blocks) > ICON_LIST_MAX_ITEMS:
        raise ValueError(
            f"layout: icon-list supports at most {ICON_LIST_MAX_ITEMS} items "
            f"({len(blocks)} given) -- split the rest onto another slide."
        )
    items: list[tuple[str, str]] = []
    for index, block in enumerate(blocks, start=1):
        match = ICON_GLYPH_RE.match(block.text)
        if match:
            glyph = match.group("glyph")
            if not SAFE_GLYPH_RE.match(glyph):
                raise ValueError(
                    f"layout: icon-list glyph {glyph!r} isn't plain ASCII -- an emoji or "
                    "other pictograph character renders using the font's own built-in "
                    "color glyph, which ignores the icon circle's accent color and looks "
                    "like a mismatched sticker (verified live: some emoji render clean, "
                    "others don't, inconsistently within the same deck). Use a bold "
                    "letter, digit(s), or one of !?*+-=/#@%& instead (e.g. 'AI', '1', "
                    "'*'), or drop the '[...]' prefix entirely to auto-number."
                )
            if WORD_LIKE_GLYPH_RE.match(glyph):
                raise ValueError(
                    f"layout: icon-list glyph {glyph!r} looks like a spelled-out word, "
                    "not a symbol -- a circle this small can't fit one legibly. Use a "
                    "single character, digit(s), or a symbol instead (e.g. '*', '1', "
                    "'AI'), or drop the '[...]' prefix entirely to auto-number."
                )
            items.append((glyph, match.group("text")))
        else:
            items.append((str(index), block.text))
    return items


def add_icon_list_slide(
    prs: PresentationType, title: str, items: list[tuple[str, str]], accent: str
) -> None:
    from pptx.dml.color import RGBColor
    from pptx.enum.dml import MSO_THEME_COLOR
    from pptx.enum.shapes import MSO_SHAPE
    from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
    from pptx.util import Pt

    slide = prs.slides.add_slide(prs.slide_layouts[TITLE_ONLY_LAYOUT])
    set_title(slide, title)

    left, top, width, height = content_area(prs)
    row_height = height // len(items)
    icon_diameter = min(int(row_height * 0.7), int(width * 0.08))
    label_gap = int(icon_diameter * 0.35)

    for index, (glyph, label) in enumerate(items):
        row_top = top + index * row_height
        icon_top = row_top + (row_height - icon_diameter) // 2
        icon = slide.shapes.add_shape(MSO_SHAPE.OVAL, left, icon_top, icon_diameter, icon_diameter)
        icon.fill.solid()
        # No explicit per-slide accent (empty string) follows the deck's
        # own theme accent color (accent1) instead of a hardcoded literal
        # -- so a write_pptx `theme` token actually reaches this shape,
        # not just the background/title text. See PPTX_DESIGN.md's
        # theme_color-migration note.
        if accent:
            icon.fill.fore_color.rgb = RGBColor.from_string(accent)  # type: ignore[no-untyped-call]
        else:
            icon.fill.fore_color.theme_color = MSO_THEME_COLOR.ACCENT_1
        icon.line.fill.background()
        icon_frame = icon.text_frame
        icon_frame.word_wrap = True
        icon_frame.vertical_anchor = MSO_ANCHOR.MIDDLE
        icon_frame.margin_left = icon_frame.margin_right = 0
        icon_frame.margin_top = icon_frame.margin_bottom = 0
        icon_paragraph = icon_frame.paragraphs[0]
        icon_paragraph.alignment = PP_ALIGN.CENTER
        icon_run = icon_paragraph.add_run()
        icon_run.text = glyph
        icon_run.font.bold = True
        icon_run.font.size = Pt(min(24, max(11, round(icon_diameter / 914400 * 22))))
        icon_run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)  # type: ignore[no-untyped-call]

        label_left = left + icon_diameter + label_gap
        label_width = left + width - label_left
        label_box = slide.shapes.add_textbox(label_left, row_top, label_width, row_height)
        label_frame = label_box.text_frame
        label_frame.word_wrap = True
        label_frame.vertical_anchor = MSO_ANCHOR.MIDDLE
        label_frame.margin_left = label_frame.margin_right = 0
        add_inline_runs(label_frame.paragraphs[0], label)


def stats_from_table(rows: list[list[str]]) -> list[tuple[str, str]]:
    """(stat, label) pairs from a `layout: stat-callout` slide's pipe-table
    -- the *same* table grammar every other table block uses, just read as
    stat/label pairs instead of rendered as a literal grid; the header row
    is discarded, mirroring `parse_chart_table`'s header/data split."""
    if len(rows) < 2:
        raise ValueError(
            "layout: stat-callout's table needs a header row plus at least one stat row."
        )
    header, *data_rows = rows
    if len(header) < 2:
        raise ValueError("layout: stat-callout's table needs a stat column and a label column.")
    if len(data_rows) > STAT_CALLOUT_MAX_ITEMS:
        raise ValueError(
            f"layout: stat-callout supports at most {STAT_CALLOUT_MAX_ITEMS} stats "
            f"({len(data_rows)} given) -- split the rest onto another slide."
        )
    pairs = [(row[0] if row else "", row[1] if len(row) > 1 else "") for row in data_rows]
    # Real, live-reproduced mistake this catches: the first column must be
    # the short headline value ("+18.4%", "62") and the second the longer
    # descriptive label ("季度营收增长") -- add_stat_callout_slide renders
    # column 0 large/bold/accent-colored and column 1 small/muted, so a
    # caller that puts the label first (an easy mix-up -- "label, value"
    # reads more naturally than "value, label" in a table) gets a card
    # with a wrapped, oversized label and a shrunken value instead of an
    # error, which only shows up as a rendering defect, not a caught
    # mistake. A stat is essentially always shorter than its own label in
    # any real KPI table, so "column 0 longer than column 1" on a
    # majority of rows is a reliable enough signal to raise instead of
    # silently rendering it backwards.
    swapped = sum(1 for stat, label in pairs if label and len(stat) > len(label))
    if swapped > len(pairs) // 2:
        raise ValueError(
            "layout: stat-callout's table columns look swapped -- the FIRST column "
            "must be the short headline value (e.g. '+18.4%', '62', '3,140') and the "
            "SECOND column the longer descriptive label (e.g. '季度营收增长'), not the "
            "other way around. Example: header '| 数值 | 指标 |', then a row like "
            "'| +18.4% | 季度营收增长 |'."
        )
    return pairs


def add_stat_callout_slide(
    prs: PresentationType, title: str, stats: list[tuple[str, str]], accent: str
) -> None:
    """Real, live-reported bug this fixes (PPTX_DESIGN.md §0): the
    previous design filled each card solid with the raw accent color and
    centered two same-weight white text lines on it -- a flat block, not
    a "designed" card. A real user directly compared this against a
    competing tool's KPI cards (light background, border only, a small
    muted label above a large emphasized number) and found ours
    noticeably worse despite being the "more native" implementation.
    Rewritten to the same light-card, real-typographic-hierarchy shape:
    white/bordered instead of solid-filled, a small muted label first,
    then a large accent-colored number -- left-aligned, not centered,
    matching the reference layout's own visual rhythm. `stats`' own
    (stat, label) tuple order/meaning is unchanged (stat is still the
    headline value); only which one renders first/larger changed."""
    from pptx.dml.color import RGBColor
    from pptx.enum.dml import MSO_THEME_COLOR
    from pptx.enum.shapes import MSO_SHAPE
    from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
    from pptx.util import Pt

    slide = prs.slides.add_slide(prs.slide_layouts[TITLE_ONLY_LAYOUT])
    set_title(slide, title)

    left, top, width, height = content_area(prs)
    gap = int(width * 0.03)
    card_width = (width - gap * (len(stats) - 1)) // len(stats)
    # 0.4, not the previous 0.7 -- a label line + one emphasized number
    # line don't need a near-square card; the previous ratio left a real
    # user-reported large empty gap at the bottom of every card, visible
    # in a rendered screenshot.
    card_height = min(height, int(card_width * 0.4))
    # Vertically centered in the content area, not anchored to its top --
    # a real, live-reproduced defect: card_height is deliberately much
    # smaller than the full content area (see the 0.4 ratio comment
    # above), and anchoring at `top` alone dumped the entire leftover
    # space below the cards as a large empty gap for the rest of the
    # slide instead of splitting it above/below.
    card_top = top + (height - card_height) // 2
    border_color = RGBColor(0xE0, 0xE0, 0xE0)  # type: ignore[no-untyped-call]
    label_color = RGBColor(0x70, 0x70, 0x70)  # type: ignore[no-untyped-call]

    for index, (stat, label) in enumerate(stats):
        card_left = left + index * (card_width + gap)
        card = slide.shapes.add_shape(
            MSO_SHAPE.ROUNDED_RECTANGLE, card_left, card_top, card_width, card_height
        )
        card.fill.solid()
        card.fill.fore_color.rgb = RGBColor(0xFF, 0xFF, 0xFF)  # type: ignore[no-untyped-call]
        card.line.color.rgb = border_color
        card.line.width = Pt(0.75)
        frame = card.text_frame
        frame.word_wrap = True
        frame.vertical_anchor = MSO_ANCHOR.TOP
        pad = int(card_width * 0.08)
        frame.margin_left = frame.margin_right = pad
        frame.margin_top = int(card_height * 0.14)
        frame.margin_bottom = pad

        label_paragraph = frame.paragraphs[0]
        label_paragraph.alignment = PP_ALIGN.LEFT
        label_run = label_paragraph.add_run()
        label_run.text = label
        label_run.font.size = Pt(12)
        label_run.font.color.rgb = label_color

        stat_paragraph = frame.add_paragraph()
        stat_paragraph.alignment = PP_ALIGN.LEFT
        stat_paragraph.space_before = Pt(8)
        stat_run = stat_paragraph.add_run()
        stat_run.text = stat
        stat_run.font.bold = True
        stat_run.font.size = Pt(28)
        # Same theme-accent-when-unspecified logic as add_icon_list_slide.
        if accent:
            stat_run.font.color.rgb = RGBColor.from_string(accent)  # type: ignore[no-untyped-call]
        else:
            stat_run.font.color.theme_color = MSO_THEME_COLOR.ACCENT_1


def split_two_column(body_text: str) -> tuple[str, str]:
    """Split a `layout: two-column` slide's post-title content on a line
    containing exactly `>>>` -- same line-scan style as the module's own
    `slide_chunks`."""
    lines = body_text.splitlines()
    marker_index = next(
        (i for i, line in enumerate(lines) if TWO_COLUMN_MARKER_RE.match(line.strip())), None
    )
    if marker_index is None:
        raise ValueError(
            "layout: two-column needs a line containing exactly '>>>' separating the "
            "left column's content from the right column's."
        )
    left = "\n".join(lines[:marker_index])
    right = "\n".join(lines[marker_index + 1 :])
    return left, right


def fill_content_placeholder(placeholder: Any, blocks: list[Block]) -> None:
    """Real, live-found bug this .clear() fixes: every existing caller
    hands this a placeholder from a slide this code itself just added
    (always empty), so appending straight into paragraphs[0] was
    invisible. fill_pptx_template reuses this same helper on an *existing*
    template slide's own body placeholder instead -- which, for any
    real-world template (a user's own uploaded .pptx, not just coscribe's
    own bundled ones, which are deliberately authored with empty
    placeholders), almost always already has real sample text and extra
    paragraphs in it. Confirmed live against a real Microsoft-authored
    template ("The science of public speaking"): without this .clear(),
    filling "NEW BULLET A" into a placeholder already containing "Know
    your material in advance" produced the single garbled run "Know your
    material in advanceNEW BULLET A", and any of the template's *original*
    paragraphs past the first one (blocks[1:] only ever *adds* new
    paragraphs, never removes old ones) survived untouched in the final
    file. TextFrame.clear()/_Paragraph.clear() are python-pptx's own
    primitives for exactly this: remove every paragraph but the first,
    then strip that first paragraph's content while preserving its
    paragraph-level formatting (alignment, bullet/indent level) so newly
    added runs still inherit the placeholder's own designed look.

    Real, live-reported bug this ``suppress_bullet_for_paragraph`` call
    fixes: this function never distinguished a markdown ``Block(kind=
    "paragraph")`` (a plain flowing line, no leading ``-``/``*``) from
    ``Block(kind="bullet")`` at the XML level -- every block just became
    a new paragraph with no bullet-related formatting touched at all.
    Harmless for coscribe's own bundled templates/write_pptx layouts,
    whose "Title and Content" placeholder happens to auto-bullet every
    paragraph by inherited layout default -- but that same inheritance
    means a single flowing paragraph (a dense-text slide, no bullets
    intended at all) rendered with a meaningless bullet glyph in front
    of it, confirmed directly against a real rendered screenshot."""
    text_frame = placeholder.text_frame
    if not blocks:
        return
    text_frame.clear()
    add_inline_runs(text_frame.paragraphs[0], blocks[0].text)
    suppress_bullet_for_paragraph(text_frame.paragraphs[0], blocks[0])
    for block in blocks[1:]:
        paragraph = text_frame.add_paragraph()
        add_inline_runs(paragraph, block.text)
        suppress_bullet_for_paragraph(paragraph, block)


def suppress_bullet_for_paragraph(paragraph: Any, block: Block) -> None:
    """No-op for bullet/number-kind blocks -- their existing, not-
    reported-as-broken behavior (inheriting whatever bullet character
    the placeholder/layout already applies) is untouched. For a plain
    ``kind="paragraph"`` block, adds an explicit ``<a:buNone/>`` to the
    paragraph's own ``<a:pPr>``, which overrides that same inherited
    default -- verified this round-trips cleanly through python-pptx
    with no schema-order issues (``<a:buNone/>`` as the sole ``pPr``
    child is always schema-valid, unlike table cell borders' fixed
    multi-child sequence, see ``set_cell_thin_bottom_border``)."""
    if block.kind != "paragraph":
        return
    from lxml import etree
    from pptx.oxml.ns import qn

    p_pr = paragraph._p.get_or_add_pPr()
    etree.SubElement(p_pr, qn("a:buNone"))


def find_body_placeholder(slide: Any, index: int = 0) -> Any | None:
    """The `index`-th (0-based, in on-slide order) non-title placeholder on
    `slide` whose type is BODY, OBJECT, or SUBTITLE -- the realistic set of
    "receives paragraph/bullet text" placeholder types a real slide can
    have (confirmed live against python-pptx's own stock layouts: "Title
    and Content" uses OBJECT for its content placeholder, not BODY; "Title
    Slide" uses SUBTITLE for its second placeholder). Used by
    fill_pptx_template/edit_pptx_text to fill an *existing* slide's own
    placeholder, unlike fill_content_placeholder's other callers, which
    always operate on a placeholder from a slide this code itself just
    added.

    `index` exists for edit_pptx_text's placeholder_index parameter --
    real templates commonly have a "two column" layout with *two*
    independent content placeholders on one slide (confirmed against a
    real Microsoft-authored template), and index=0 (the default, and
    fill_pptx_template's only behavior) can only ever reach the first one.

    Real, live-found bug this .has_text_frame check fixes: an OBJECT
    placeholder slot can already hold a native table (a GraphicFrame, not
    a text-frame shape) rather than plain text -- confirmed against a real
    Microsoft-authored template whose "Agenda" slide's content placeholder
    was exactly this. Without the check, this function still matched it
    (its placeholder_format.type is OBJECT same as a text one), and the
    caller's `.text_frame` access below crashed with an opaque
    AttributeError: 'PlaceholderGraphicFrame' object has no attribute
    'text_frame' instead of the same clean, actionable "no body/content
    placeholder" ValueError a slide with no eligible placeholder at all
    already produces -- treating a table-holding slot as ineligible here
    gets both cases the same clear error."""
    from pptx.enum.shapes import PP_PLACEHOLDER

    eligible = {PP_PLACEHOLDER.BODY, PP_PLACEHOLDER.OBJECT, PP_PLACEHOLDER.SUBTITLE}
    title_shape = slide.shapes.title
    matches = []
    for placeholder in slide.placeholders:
        if title_shape is not None and placeholder.shape_id == title_shape.shape_id:
            continue
        if placeholder.placeholder_format.type in eligible and placeholder.has_text_frame:
            matches.append(placeholder)
    if index < 0 or index >= len(matches):
        return None
    return matches[index]


def add_two_column_slide(
    prs: PresentationType, title: str, left_blocks: list[Block], right_blocks: list[Block]
) -> None:
    slide = prs.slides.add_slide(prs.slide_layouts[TWO_CONTENT_LAYOUT])
    set_title(slide, title)
    fill_content_placeholder(slide.placeholders[1], left_blocks)
    fill_content_placeholder(slide.placeholders[2], right_blocks)
