from pathlib import Path

from .helpers import (
    _tools_by_name,
)


def test_table_slide_strips_default_style_and_uses_hairline_borders(tmp_path: Path) -> None:
    """Regression test for PPTX_DESIGN.md §0's real, user-reported visual-
    quality defect: a table built with no styling at all renders with
    PowerPoint's default banded-blue table style, which a real user
    directly compared against a competing tool's plainer-but-deliberately-
    designed table and found worse. Asserts the default style is actually
    stripped (first_row/horz_banding off) and every cell's tcPr border
    children are in ECMA-376's required schema order (lnL, lnR, lnT, lnB,
    then a fill element) -- inserting out of order round-trips fine
    through python-pptx's own lenient reader but real PowerPoint enforces
    the schema strictly, so this is the one thing a plain re-read can't
    catch on its own."""
    from pptx import Presentation

    tools = _tools_by_name(tmp_path)
    content = (
        "# Regions\n"
        "| Region | Rep | Attainment |\n"
        "| --- | --- | --- |\n"
        "| North | Ada | 112% |\n"
        "| South | Bo | 98% |\n"
    )
    tools["write_pptx"](path="deck.pptx", content=content)

    prs = Presentation(str(tmp_path / "deck.pptx"))
    table = next(s for s in prs.slides[0].shapes if s.has_table).table
    assert table.first_row is False
    assert table.horz_banding is False

    for row_index in range(len(table.rows)):
        for col_index in range(len(table.columns)):
            tc_pr = table.cell(row_index, col_index)._tc.get_or_add_tcPr()
            tags = [child.tag.split("}")[-1] for child in tc_pr]
            border_tags = [t for t in tags if t in ("lnL", "lnR", "lnT", "lnB")]
            assert border_tags == ["lnL", "lnR", "lnT", "lnB"]
            fill_index = next(i for i, t in enumerate(tags) if t in ("noFill", "solidFill"))
            assert fill_index == len(border_tags)  # every ln* comes before the fill


def test_table_slide_right_aligns_numeric_cells_and_flags_over_100_percent(
    tmp_path: Path,
) -> None:
    from pptx import Presentation
    from pptx.enum.dml import MSO_THEME_COLOR
    from pptx.enum.text import PP_ALIGN

    tools = _tools_by_name(tmp_path)
    content = (
        "# Regions\n"
        "| Region | Rep | Attainment |\n"
        "| --- | --- | --- |\n"
        "| North | Ada | 112% |\n"
        "| South | Bo | 98% |\n"
    )
    tools["write_pptx"](path="deck.pptx", content=content)

    prs = Presentation(str(tmp_path / "deck.pptx"))
    table = next(s for s in prs.slides[0].shapes if s.has_table).table

    header_cell = table.cell(0, 0)
    assert header_cell.text_frame.paragraphs[0].alignment == PP_ALIGN.LEFT
    assert header_cell.text_frame.paragraphs[0].runs[0].font.bold is True
    # theme_color, not a literal RGB, so a table stays readable if
    # write_pptx's `theme` parameter later sets a dark background --
    # see test_table_text_follows_theme_text_token below.
    assert header_cell.text_frame.paragraphs[0].runs[0].font.color.theme_color == (
        MSO_THEME_COLOR.DARK_1
    )

    region_cell = table.cell(1, 0)  # "North" -- not numeric-looking
    assert region_cell.text_frame.paragraphs[0].alignment == PP_ALIGN.LEFT

    over_100_cell = table.cell(1, 2)  # "112%"
    assert over_100_cell.text_frame.paragraphs[0].alignment == PP_ALIGN.RIGHT
    over_100_run = over_100_cell.text_frame.paragraphs[0].runs[0]
    assert over_100_run.font.bold is True
    assert str(over_100_run.font.color.rgb) == "B3261E"

    under_100_cell = table.cell(2, 2)  # "98%"
    under_100_run = under_100_cell.text_frame.paragraphs[0].runs[0]
    assert under_100_run.font.bold is not True
    assert under_100_run.font.color.theme_color == MSO_THEME_COLOR.DARK_1


def test_stat_callout_cards_are_bordered_not_solid_filled_with_hierarchy(
    tmp_path: Path,
) -> None:
    """Regression test for PPTX_DESIGN.md §0's other reported defect: cards
    used to fill solid with the accent color and center two same-weight
    white lines -- a flat block, not a "designed" card. Asserts the new
    shape: white/bordered card, muted label first (smaller), accent-
    colored emphasized stat second (larger), both left-aligned."""
    from pptx import Presentation
    from pptx.enum.text import PP_ALIGN

    tools = _tools_by_name(tmp_path)
    content = (
        "layout: stat-callout 1E2761\n"
        "# Highlights\n"
        "| Stat | Label |\n"
        "| --- | --- |\n"
        "| 3x | Revenue growth |\n"
        "| 98% | Retention |\n"
    )
    tools["write_pptx"](path="deck.pptx", content=content)

    prs = Presentation(str(tmp_path / "deck.pptx"))
    cards = [s for s in prs.slides[0].shapes if s.shape_type == 1]
    card = next(c for c in cards if "3x" in c.text_frame.text)

    assert card.fill.type is not None
    assert str(card.fill.fore_color.rgb) == "FFFFFF"
    assert str(card.line.color.rgb) == "E0E0E0"

    label_paragraph, stat_paragraph = card.text_frame.paragraphs
    assert label_paragraph.alignment == PP_ALIGN.LEFT
    assert label_paragraph.text == "Revenue growth"
    label_run = label_paragraph.runs[0]
    assert label_run.font.size.pt == 12
    assert str(label_run.font.color.rgb) == "707070"

    assert stat_paragraph.alignment == PP_ALIGN.LEFT
    assert stat_paragraph.text == "3x"
    stat_run = stat_paragraph.runs[0]
    assert stat_run.font.bold is True
    assert stat_run.font.size.pt == 28
    assert str(stat_run.font.color.rgb) == "1E2761"


def test_table_slide_is_centered_on_the_real_widescreen_slide(tmp_path: Path) -> None:
    """Regression test for a real, user-reported bug caught in a rendered
    screenshot: the table's position used to be hardcoded for python-
    pptx's own default 10in-wide blank Presentation(), but write_pptx
    always resizes the deck to widescreen (13.333in) -- on the real
    width the table actually renders at, that left a large dead gap on
    the right, visibly off-center. Asserts the table's left and right
    margins are now equal."""
    from pptx import Presentation

    tools = _tools_by_name(tmp_path)
    content = "# Regions\n| Region | Attainment |\n| --- | --- |\n| North | 112% |\n"
    tools["write_pptx"](path="deck.pptx", content=content)

    prs = Presentation(str(tmp_path / "deck.pptx"))
    table_shape = next(s for s in prs.slides[0].shapes if s.has_table)
    left_margin = table_shape.left
    right_margin = prs.slide_width - (table_shape.left + table_shape.width)
    assert left_margin == right_margin


def test_stat_callout_card_height_is_not_mostly_empty_space(tmp_path: Path) -> None:
    """Regression test for a real, user-reported bug caught in a rendered
    screenshot: a card sized for a near-square aspect ratio left a large
    empty gap below its two short text lines (a label + one emphasized
    number). Asserts the card's height/width ratio is meaningfully
    smaller than the old 0.7 default, without pinning an exact value.
    Uses 3 stats, not 1 -- with only one card spanning the full content
    width, height was already capped by the content area's own height
    regardless of the width-derived multiplier, masking the old 0.7
    ratio entirely (confirmed: this test genuinely fails against the
    pre-fix code only with multiple, narrower cards)."""
    from pptx import Presentation

    tools = _tools_by_name(tmp_path)
    content = (
        "layout: stat-callout\n"
        "# Highlights\n"
        "| Stat | Label |\n"
        "| --- | --- |\n"
        "| 3x | Revenue growth |\n"
        "| 12 | New markets |\n"
        "| 98% | Retention |\n"
    )
    tools["write_pptx"](path="deck.pptx", content=content)

    prs = Presentation(str(tmp_path / "deck.pptx"))
    card = next(s for s in prs.slides[0].shapes if s.shape_type == 1)
    assert card.height / card.width < 0.5


def test_plain_paragraph_body_text_has_no_bullet_marker(tmp_path: Path) -> None:
    """Regression test for a real, user-reported bug caught in a rendered
    screenshot: a slide with a single flowing paragraph (no leading -/*,
    so Block(kind="paragraph")) rendered with a meaningless bullet glyph
    in front of it, because the "Title and Content" placeholder this
    lands in auto-bullets every paragraph by inherited layout default
    and nothing ever overrode that for plain-paragraph content. Asserts
    the paragraph's own <a:pPr> now has an explicit <a:buNone/>."""
    from pptx import Presentation
    from pptx.oxml.ns import qn

    tools = _tools_by_name(tmp_path)
    content = "# Context\nA single flowing paragraph, not a list item at all.\n"
    tools["write_pptx"](path="deck.pptx", content=content)

    prs = Presentation(str(tmp_path / "deck.pptx"))
    slide = prs.slides[0]
    body = next(
        p
        for p in slide.placeholders
        if p.placeholder_format.idx != slide.shapes.title.placeholder_format.idx
    )
    p_pr = body.text_frame.paragraphs[0]._p.find(qn("a:pPr"))
    assert p_pr is not None
    assert p_pr.find(qn("a:buNone")) is not None


def test_bullet_body_text_still_has_no_explicit_bullet_override(tmp_path: Path) -> None:
    """A real markdown bullet (leading "-") must NOT get the paragraph-
    kind buNone override -- its existing, not-reported-as-broken
    behavior (inheriting the placeholder's own bullet character) stays
    exactly as it was."""
    from pptx import Presentation
    from pptx.oxml.ns import qn

    tools = _tools_by_name(tmp_path)
    content = "# Context\n- a real bullet point\n"
    tools["write_pptx"](path="deck.pptx", content=content)

    prs = Presentation(str(tmp_path / "deck.pptx"))
    slide = prs.slides[0]
    body = next(
        p
        for p in slide.placeholders
        if p.placeholder_format.idx != slide.shapes.title.placeholder_format.idx
    )
    p_pr = body.text_frame.paragraphs[0]._p.find(qn("a:pPr"))
    assert p_pr is None or p_pr.find(qn("a:buNone")) is None
