from pathlib import Path

import pytest

from coscribe.tools.office.pptx.qa import (
    check_missing_visual_elements,
    check_text_overlaps,
)

from .helpers import (
    _libreoffice_actually_works,
    _tools_by_name,
)

# --- Prefab layout library (layout: icon-list / stat-callout / two-column) ---


def test_layout_icon_list_renders_glyphs_labels_and_stays_clean(tmp_path: Path) -> None:
    from pptx import Presentation

    tools = _tools_by_name(tmp_path)
    content = (
        "layout: icon-list FF0000\n"
        "# Feature Highlights\n"
        "- [*] Real-time energy tracking\n"
        "- Mobile app control\n"
    )
    tools["write_pptx"](path="deck.pptx", content=content)

    prs = Presentation(str(tmp_path / "deck.pptx"))
    slide = prs.slides[0]
    icon_texts = [
        shape.text_frame.text
        for shape in slide.shapes
        if shape.shape_type == 1  # AUTO_SHAPE
    ]
    label_texts = [
        shape.text_frame.text
        for shape in slide.shapes
        if shape.shape_type == 17  # TEXT_BOX
    ]
    assert icon_texts == ["*", "2"]
    assert label_texts == ["Real-time energy tracking", "Mobile app control"]
    assert check_text_overlaps(prs) == []
    assert check_missing_visual_elements(prs) == []


def test_layout_omitted_produces_the_same_slide_as_before(tmp_path: Path) -> None:
    from pptx import Presentation

    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- first\n- second")

    prs = Presentation(str(tmp_path / "deck.pptx"))
    slide = prs.slides[0]
    body_text = slide.placeholders[1].text_frame.text
    assert body_text == "first\nsecond"
    assert len(slide.shapes) == 2  # title + body placeholder only, no new shapes


def test_layout_icon_list_rejects_too_many_items(tmp_path: Path) -> None:
    tools = _tools_by_name(tmp_path)
    bullets = "\n".join(f"- item {i}" for i in range(7))
    content = f"layout: icon-list\n# Title\n{bullets}\n"

    with pytest.raises(ValueError, match="at most 6 items"):
        tools["write_pptx"](path="deck.pptx", content=content)


def test_layout_icon_list_rejects_a_table(tmp_path: Path) -> None:
    tools = _tools_by_name(tmp_path)
    content = "layout: icon-list\n# Title\n| a | b |\n| --- | --- |\n| 1 | 2 |\n"

    with pytest.raises(ValueError, match="doesn't support tables"):
        tools["write_pptx"](path="deck.pptx", content=content)


def test_layout_icon_list_rejects_a_spelled_out_word_glyph(tmp_path: Path) -> None:
    # Live-reproduced defect: a real model wrote "- [dash] Rising costs..."
    # (a plain English word, not a symbol), which rendered as ugly wrapped
    # text inside the small icon circle.
    tools = _tools_by_name(tmp_path)
    content = "layout: icon-list\n# Title\n- [dash] Rising costs\n"

    with pytest.raises(ValueError, match="spelled-out word"):
        tools["write_pptx"](path="deck.pptx", content=content)


def test_layout_icon_list_rejects_an_emoji_glyph(tmp_path: Path) -> None:
    # Live-reproduced defect: an emoji glyph (e.g. a "house" or "rocket"
    # character) renders via the font's own built-in color glyph, ignoring
    # the icon circle's accent-color fill -- some icons come out clean,
    # others as a mismatched full-color sticker, inconsistently.
    tools = _tools_by_name(tmp_path)
    content = "layout: icon-list\n# Title\n- [\U0001f680] Launch\n"

    with pytest.raises(ValueError, match="isn't plain ASCII"):
        tools["write_pptx"](path="deck.pptx", content=content)


def test_layout_icon_list_allows_short_initials_as_a_glyph(tmp_path: Path) -> None:
    from pptx import Presentation

    tools = _tools_by_name(tmp_path)
    content = "layout: icon-list\n# Title\n- [AI] Smart recommendations\n"
    tools["write_pptx"](path="deck.pptx", content=content)

    prs = Presentation(str(tmp_path / "deck.pptx"))
    icon_texts = [shape.text_frame.text for shape in prs.slides[0].shapes if shape.shape_type == 1]
    assert icon_texts == ["AI"]


def test_layout_stat_callout_renders_cards_and_stays_clean(tmp_path: Path) -> None:
    from pptx import Presentation

    tools = _tools_by_name(tmp_path)
    content = (
        "layout: stat-callout 028090\n"
        "# Q4 Highlights\n"
        "| Stat | Label |\n"
        "| --- | --- |\n"
        "| 3x | Revenue growth |\n"
        "| 12 | New markets |\n"
        "| 98% | Retention |\n"
    )
    tools["write_pptx"](path="deck.pptx", content=content)

    prs = Presentation(str(tmp_path / "deck.pptx"))
    card_texts = sorted(
        shape.text_frame.text
        for shape in prs.slides[0].shapes
        if shape.shape_type == 1  # AUTO_SHAPE
    )
    # label first, then the emphasized stat -- see _add_stat_callout_slide's
    # own docstring (PPTX_DESIGN.md §0) for why this reads label-then-value
    # now instead of value-then-label.
    assert card_texts == ["New markets\n12", "Retention\n98%", "Revenue growth\n3x"]
    assert check_text_overlaps(prs) == []
    assert check_missing_visual_elements(prs) == []


def test_layout_stat_callout_rejects_bullets_instead_of_a_table(tmp_path: Path) -> None:
    tools = _tools_by_name(tmp_path)
    content = "layout: stat-callout\n# Title\n- not a table\n"

    with pytest.raises(ValueError, match="exactly one pipe-table"):
        tools["write_pptx"](path="deck.pptx", content=content)


def test_layout_stat_callout_rejects_too_many_rows(tmp_path: Path) -> None:
    tools = _tools_by_name(tmp_path)
    rows = "\n".join(f"| {i} | label {i} |" for i in range(5))
    content = f"layout: stat-callout\n# Title\n| Stat | Label |\n| --- | --- |\n{rows}\n"

    with pytest.raises(ValueError, match="at most 4 stats"):
        tools["write_pptx"](path="deck.pptx", content=content)


def test_layout_stat_callout_rejects_swapped_columns(tmp_path: Path) -> None:
    """Real, live-reproduced mistake: writing the table as
    '| label | value |' (which reads more naturally than '| value |
    label |') silently rendered the long label large/bold/accent-colored
    and the short value small/muted -- the exact opposite of the intended
    hierarchy -- with no error, only a visible defect in the rendered
    deck. Must now raise instead."""
    tools = _tools_by_name(tmp_path)
    content = (
        "layout: stat-callout\n"
        "# Highlights\n"
        "| Label | Value |\n"
        "| --- | --- |\n"
        "| Quarterly revenue growth | +18.4% |\n"
        "| Net revenue retention | 121% |\n"
        "| Customer satisfaction NPS | 62 |\n"
    )

    with pytest.raises(ValueError, match="columns look swapped"):
        tools["write_pptx"](path="deck.pptx", content=content)


def test_layout_stat_callout_cards_are_vertically_centered(tmp_path: Path) -> None:
    """Real, live-reported defect caught in a rendered screenshot: cards
    anchored to the top of the content area left a large empty gap for
    the rest of the slide below them, since card_height is deliberately
    much shorter than the full content area (see _add_stat_callout_slide's
    own comment). Cards should split the leftover space above/below
    instead of dumping all of it below."""
    from pptx import Presentation

    from coscribe.tools.office.pptx.slide_builders import content_area

    tools = _tools_by_name(tmp_path)
    content = (
        "layout: stat-callout\n"
        "# Highlights\n"
        "| Stat | Label |\n"
        "| --- | --- |\n"
        "| 3x | Revenue growth |\n"
    )
    tools["write_pptx"](path="deck.pptx", content=content)

    prs = Presentation(tmp_path / "deck.pptx")
    _left, content_top, _width, _height = content_area(prs)
    card = next(s for s in prs.slides[0].shapes if s.shape_type == 1)
    assert card.top > content_top


def test_layout_two_column_splits_content_at_marker(tmp_path: Path) -> None:
    from pptx import Presentation

    tools = _tools_by_name(tmp_path)
    content = (
        "layout: two-column\n"
        "# Before vs After\n"
        "- Manual tracking\n"
        "- No alerts\n"
        ">>>\n"
        "- Real-time dashboards\n"
        "- Proactive alerts\n"
    )
    tools["write_pptx"](path="deck.pptx", content=content)

    prs = Presentation(str(tmp_path / "deck.pptx"))
    slide = prs.slides[0]
    assert slide.shapes.title.text == "Before vs After"
    assert slide.placeholders[1].text_frame.text == "Manual tracking\nNo alerts"
    assert slide.placeholders[2].text_frame.text == "Real-time dashboards\nProactive alerts"


def test_layout_two_column_requires_the_marker(tmp_path: Path) -> None:
    tools = _tools_by_name(tmp_path)
    content = "layout: two-column\n# Title\n- only one column\n"

    with pytest.raises(ValueError, match="'>>>'"):
        tools["write_pptx"](path="deck.pptx", content=content)


def test_layout_two_column_rejects_a_table_on_either_side(tmp_path: Path) -> None:
    tools = _tools_by_name(tmp_path)
    content = "layout: two-column\n# Title\n| a | b |\n| --- | --- |\n| 1 | 2 |\n>>>\n- right\n"

    with pytest.raises(ValueError, match="doesn't support tables"):
        tools["write_pptx"](path="deck.pptx", content=content)


def test_layout_two_column_flags_missing_visual_element_by_design(tmp_path: Path) -> None:
    from pptx import Presentation

    tools = _tools_by_name(tmp_path)
    content = "layout: two-column\n# Title\n- left\n>>>\n- right\n"
    tools["write_pptx"](path="deck.pptx", content=content)

    prs = Presentation(str(tmp_path / "deck.pptx"))
    # Documented exception: two-column is plain text by construction (the
    # stock "Two Content" layout has no shape of its own), so this flags
    # unless the model separately adds a chart/image -- intended, not a bug.
    assert check_missing_visual_elements(prs) == [1]
    assert check_text_overlaps(prs) == []


def test_layout_unknown_id_raises_naming_valid_ids(tmp_path: Path) -> None:
    tools = _tools_by_name(tmp_path)
    content = "layout: bogus-id\n# Title\n- body\n"

    with pytest.raises(
        ValueError, match="Unknown layout.*icon-list.*stat-callout.*svg.*two-column"
    ):
        tools["write_pptx"](path="deck.pptx", content=content)


def test_layout_two_column_with_undersized_template_raises(tmp_path: Path) -> None:
    from pptx import Presentation
    from pptx.oxml.ns import qn

    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="template.pptx", content="# Old\n- old bullet")

    # Same technique as test_write_pptx_with_template_missing_required_layouts_raises:
    # strip every layout but the first, leaving fewer than write_pptx needs
    # -- index 3 ("Two Content") is well within what gets stripped here.
    prs = Presentation(tmp_path / "template.pptx")
    layout_master = prs.slide_masters[0]
    sld_layout_id_lst = layout_master.element.find(qn("p:sldLayoutIdLst"))
    for layout_id in list(sld_layout_id_lst)[1:]:
        r_id = layout_id.get(qn("r:id"))
        layout_master.part.drop_rel(r_id)
        sld_layout_id_lst.remove(layout_id)
    prs.save(tmp_path / "template.pptx")

    content = "layout: two-column\n# Title\n- left\n>>>\n- right\n"
    with pytest.raises(ValueError, match="slide layout"):
        tools["write_pptx"](path="deck.pptx", content=content, template_path="template.pptx")


def test_layout_svg_renders_background_circle_and_text_and_stays_clean(
    tmp_path: Path,
) -> None:
    from pptx import Presentation
    from pptx.dml.color import RGBColor

    tools = _tools_by_name(tmp_path)
    svg_markup = (
        '<svg width="960" height="540" viewBox="0 0 960 540">'
        '<rect x="0" y="0" width="960" height="540" fill="#1E2761"/>'
        '<circle cx="120" cy="270" r="40" fill="FF0000"/>'
        '<text x="220" y="260" font-size="36" fill="#FFFFFF">Real-time tracking</text>'
        '<text x="60" y="80" font-size="48" fill="#FFFFFF">Aurora</text>'
        "</svg>"
    )
    content = f"layout: svg\n{svg_markup}\n"
    tools["write_pptx"](path="deck.pptx", content=content)

    prs = Presentation(str(tmp_path / "deck.pptx"))
    slide = prs.slides[0]
    # The full-canvas rect at index 0 is promoted to the slide background
    # rather than becoming its own shape -- only the circle and two text
    # boxes remain as real shapes.
    assert len(slide.shapes) == 3
    assert slide.background.fill.fore_color.rgb == RGBColor.from_string("1E2761")
    text_shapes = [s for s in slide.shapes if s.has_text_frame and s.shape_type == 17]
    assert sorted(s.text_frame.text for s in text_shapes) == ["Aurora", "Real-time tracking"]
    assert check_text_overlaps(prs) == []
    assert check_missing_visual_elements(prs) == []


def test_layout_svg_rx_selects_rounded_rectangle_without_rx_selects_rectangle(
    tmp_path: Path,
) -> None:
    from pptx import Presentation
    from pptx.enum.shapes import MSO_SHAPE

    tools = _tools_by_name(tmp_path)
    svg_markup = (
        '<svg width="960" height="540" viewBox="0 0 960 540">'
        '<rect x="10" y="10" width="200" height="80" fill="FF0000"/>'
        '<rect x="10" y="120" width="200" height="80" rx="12" fill="00FF00"/>'
        "</svg>"
    )
    tools["write_pptx"](path="deck.pptx", content=f"layout: svg\n{svg_markup}\n")

    prs = Presentation(str(tmp_path / "deck.pptx"))
    shapes = list(prs.slides[0].shapes)
    assert len(shapes) == 2
    assert shapes[0].auto_shape_type == MSO_SHAPE.RECTANGLE
    assert shapes[1].auto_shape_type == MSO_SHAPE.ROUNDED_RECTANGLE


def test_layout_svg_accepts_hex_and_named_colors_rejects_unknown_name(
    tmp_path: Path,
) -> None:
    from pptx import Presentation
    from pptx.dml.color import RGBColor

    tools = _tools_by_name(tmp_path)
    svg_markup = (
        '<svg width="960" height="540" viewBox="0 0 960 540">'
        '<rect x="10" y="10" width="200" height="80" fill="FF0000"/>'
        '<rect x="10" y="120" width="200" height="80" fill="#00FF00"/>'
        '<rect x="10" y="230" width="200" height="80" fill="navy"/>'
        "</svg>"
    )
    tools["write_pptx"](path="deck.pptx", content=f"layout: svg\n{svg_markup}\n")

    prs = Presentation(str(tmp_path / "deck.pptx"))
    fills = [s.fill.fore_color.rgb for s in prs.slides[0].shapes]
    assert fills == [
        RGBColor.from_string("FF0000"),
        RGBColor.from_string("00FF00"),
        RGBColor.from_string("000080"),
    ]

    bad_svg = (
        '<svg width="100" height="100" viewBox="0 0 100 100">'
        '<rect x="0" y="0" width="50" height="50" fill="notacolor"/>'
        "</svg>"
    )
    with pytest.raises(ValueError, match="not a 6-hex-digit color"):
        tools["write_pptx"](path="deck2.pptx", content=f"layout: svg\n{bad_svg}\n")


def test_layout_svg_rejects_unsupported_element_naming_run_node_script(
    tmp_path: Path,
) -> None:
    tools = _tools_by_name(tmp_path)
    svg_markup = (
        '<svg width="100" height="100" viewBox="0 0 100 100">'
        '<image href="photo.png" x="0" y="0" width="100" height="100"/>'
        "</svg>"
    )
    with pytest.raises(ValueError, match="run_node_script"):
        tools["write_pptx"](path="deck.pptx", content=f"layout: svg\n{svg_markup}\n")


def test_layout_svg_path_straight_lines_renders_a_freeform_shape(tmp_path: Path) -> None:
    from pptx import Presentation
    from pptx.dml.color import RGBColor
    from pptx.enum.shapes import MSO_SHAPE_TYPE

    tools = _tools_by_name(tmp_path)
    svg_markup = (
        '<svg width="200" height="200" viewBox="0 0 200 200">'
        '<path d="M10,10 L190,10 L100,190 Z" fill="FF0000"/>'
        "</svg>"
    )
    tools["write_pptx"](path="deck.pptx", content=f"layout: svg\n{svg_markup}\n")

    prs = Presentation(str(tmp_path / "deck.pptx"))
    shapes = list(prs.slides[0].shapes)
    assert len(shapes) == 1
    assert shapes[0].shape_type == MSO_SHAPE_TYPE.FREEFORM
    assert shapes[0].fill.fore_color.rgb == RGBColor.from_string("FF0000")
    assert check_missing_visual_elements(prs) == []


def test_layout_svg_path_bezier_curves_render_without_error(tmp_path: Path) -> None:
    from pptx import Presentation
    from pptx.enum.shapes import MSO_SHAPE_TYPE

    tools = _tools_by_name(tmp_path)
    svg_markup = (
        '<svg width="200" height="200" viewBox="0 0 200 200">'
        '<path d="M20,100 C20,20 180,20 180,100 Q180,180 100,180 Z" fill="00FF00"/>'
        "</svg>"
    )
    tools["write_pptx"](path="deck.pptx", content=f"layout: svg\n{svg_markup}\n")

    prs = Presentation(str(tmp_path / "deck.pptx"))
    shape = next(iter(prs.slides[0].shapes))
    assert shape.shape_type == MSO_SHAPE_TYPE.FREEFORM
    # Bounding box spans the full extent of the curve's control points too
    # (a safe overestimate, not a pixel-tight fit -- see module docstring).
    assert shape.width > 0
    assert shape.height > 0


def test_layout_svg_path_relative_commands_match_absolute_equivalent(tmp_path: Path) -> None:
    from pptx import Presentation

    tools = _tools_by_name(tmp_path)
    absolute_svg = (
        '<svg width="200" height="200" viewBox="0 0 200 200">'
        '<path d="M10,10 L100,10 L100,100 Z" fill="0000FF"/>'
        "</svg>"
    )
    relative_svg = (
        '<svg width="200" height="200" viewBox="0 0 200 200">'
        '<path d="m10,10 l90,0 l0,90 z" fill="0000FF"/>'
        "</svg>"
    )
    tools["write_pptx"](path="abs.pptx", content=f"layout: svg\n{absolute_svg}\n")
    tools["write_pptx"](path="rel.pptx", content=f"layout: svg\n{relative_svg}\n")

    abs_shape = next(iter(Presentation(str(tmp_path / "abs.pptx")).slides[0].shapes))
    rel_shape = next(iter(Presentation(str(tmp_path / "rel.pptx")).slides[0].shapes))
    assert (abs_shape.left, abs_shape.top, abs_shape.width, abs_shape.height) == (
        rel_shape.left,
        rel_shape.top,
        rel_shape.width,
        rel_shape.height,
    )


def test_layout_svg_path_implicit_repeat_commands_add_extra_segments(tmp_path: Path) -> None:
    from pptx import Presentation

    tools = _tools_by_name(tmp_path)
    # "L100,0 100,100" repeats L implicitly for the second pair -- same
    # shape as writing out "L100,0 L100,100" explicitly.
    implicit_svg = (
        '<svg width="200" height="200" viewBox="0 0 200 200">'
        '<path d="M0,0 L100,0 100,100 L0,100 Z" fill="FF0000"/>'
        "</svg>"
    )
    explicit_svg = (
        '<svg width="200" height="200" viewBox="0 0 200 200">'
        '<path d="M0,0 L100,0 L100,100 L0,100 Z" fill="FF0000"/>'
        "</svg>"
    )
    tools["write_pptx"](path="implicit.pptx", content=f"layout: svg\n{implicit_svg}\n")
    tools["write_pptx"](path="explicit.pptx", content=f"layout: svg\n{explicit_svg}\n")

    implicit_shape = next(iter(Presentation(str(tmp_path / "implicit.pptx")).slides[0].shapes))
    explicit_shape = next(iter(Presentation(str(tmp_path / "explicit.pptx")).slides[0].shapes))
    assert (implicit_shape.width, implicit_shape.height) == (
        explicit_shape.width,
        explicit_shape.height,
    )


def test_layout_svg_path_rejects_unsupported_command_naming_run_node_script(
    tmp_path: Path,
) -> None:
    tools = _tools_by_name(tmp_path)
    svg_markup = (
        '<svg width="100" height="100" viewBox="0 0 100 100">'
        '<path d="M10,10 A50,50 0 0 1 90,90" fill="FF0000"/>'
        "</svg>"
    )
    with pytest.raises(ValueError, match="run_node_script"):
        tools["write_pptx"](path="deck.pptx", content=f"layout: svg\n{svg_markup}\n")


def test_layout_svg_path_requires_starting_moveto(tmp_path: Path) -> None:
    tools = _tools_by_name(tmp_path)
    svg_markup = (
        '<svg width="100" height="100" viewBox="0 0 100 100"><path d="L90,90" fill="FF0000"/></svg>'
    )
    with pytest.raises(ValueError, match="moveto"):
        tools["write_pptx"](path="deck.pptx", content=f"layout: svg\n{svg_markup}\n")


def test_layout_svg_path_rejects_bare_moveto_with_no_drawing_command(tmp_path: Path) -> None:
    tools = _tools_by_name(tmp_path)
    svg_markup = (
        '<svg width="100" height="100" viewBox="0 0 100 100"><path d="M10,10" fill="FF0000"/></svg>'
    )
    with pytest.raises(ValueError, match="at least one drawing command"):
        tools["write_pptx"](path="deck.pptx", content=f"layout: svg\n{svg_markup}\n")


def test_layout_svg_path_rejects_missing_d_attribute(tmp_path: Path) -> None:
    tools = _tools_by_name(tmp_path)
    svg_markup = '<svg width="100" height="100" viewBox="0 0 100 100"><path fill="FF0000"/></svg>'
    with pytest.raises(ValueError, match="needs a d attribute"):
        tools["write_pptx"](path="deck.pptx", content=f"layout: svg\n{svg_markup}\n")


def test_layout_svg_linear_gradient_fill_applies_to_a_shape(tmp_path: Path) -> None:
    from pptx import Presentation
    from pptx.enum.dml import MSO_FILL_TYPE

    tools = _tools_by_name(tmp_path)
    svg_markup = (
        '<svg width="200" height="200" viewBox="0 0 200 200">'
        '<defs><linearGradient id="g1" x1="0%" y1="0%" x2="100%" y2="0%">'
        '<stop offset="0%" stop-color="#FF0000"/>'
        '<stop offset="100%" stop-color="#0000FF"/>'
        "</linearGradient></defs>"
        '<rect x="10" y="10" width="100" height="100" fill="url(#g1)"/>'
        "</svg>"
    )
    tools["write_pptx"](path="deck.pptx", content=f"layout: svg\n{svg_markup}\n")

    prs = Presentation(str(tmp_path / "deck.pptx"))
    shape = next(iter(prs.slides[0].shapes))
    assert shape.fill.type == MSO_FILL_TYPE.GRADIENT
    stops = shape.fill.gradient_stops
    assert len(stops) == 2
    # x1=0,y1=0 -> x2=100%,y2=0 is a pure left-to-right vector, DrawingML's
    # own 0-degree default.
    assert shape.fill.gradient_angle == pytest.approx(0.0)


def test_layout_svg_radial_gradient_fill_applies_to_a_shape(tmp_path: Path) -> None:
    from pptx import Presentation
    from pptx.enum.dml import MSO_FILL_TYPE

    tools = _tools_by_name(tmp_path)
    svg_markup = (
        '<svg width="200" height="200" viewBox="0 0 200 200">'
        '<radialGradient id="g1">'
        '<stop offset="0%" stop-color="white"/>'
        '<stop offset="100%" stop-color="navy"/>'
        "</radialGradient>"
        '<circle cx="100" cy="100" r="80" fill="url(#g1)"/>'
        "</svg>"
    )
    tools["write_pptx"](path="deck.pptx", content=f"layout: svg\n{svg_markup}\n")

    prs = Presentation(str(tmp_path / "deck.pptx"))
    shape = next(iter(prs.slides[0].shapes))
    assert shape.fill.type == MSO_FILL_TYPE.GRADIENT
    with pytest.raises(ValueError, match="not a linear gradient"):
        _ = shape.fill.gradient_angle


def test_layout_svg_gradient_background_rect_is_promoted_to_slide_background(
    tmp_path: Path,
) -> None:
    from pptx import Presentation

    tools = _tools_by_name(tmp_path)
    svg_markup = (
        '<svg width="200" height="200" viewBox="0 0 200 200">'
        '<linearGradient id="bg"><stop offset="0%" stop-color="black"/>'
        '<stop offset="100%" stop-color="white"/></linearGradient>'
        '<rect x="0" y="0" width="200" height="200" fill="url(#bg)"/>'
        '<circle cx="100" cy="100" r="20" fill="red"/>'
        "</svg>"
    )
    tools["write_pptx"](path="deck.pptx", content=f"layout: svg\n{svg_markup}\n")

    prs = Presentation(str(tmp_path / "deck.pptx"))
    slide = prs.slides[0]
    # Full-canvas rect promoted to slide background, not left as a shape.
    assert len(slide.shapes) == 1
    from pptx.enum.dml import MSO_FILL_TYPE

    assert slide.background.fill.type == MSO_FILL_TYPE.GRADIENT


def test_layout_svg_gradient_rejects_unknown_id(tmp_path: Path) -> None:
    tools = _tools_by_name(tmp_path)
    svg_markup = (
        '<svg width="100" height="100" viewBox="0 0 100 100">'
        '<rect x="0" y="0" width="50" height="50" fill="url(#missing)"/>'
        "</svg>"
    )
    with pytest.raises(ValueError, match="no <linearGradient>/<radialGradient>"):
        tools["write_pptx"](path="deck.pptx", content=f"layout: svg\n{svg_markup}\n")


def test_layout_svg_gradient_requires_at_least_two_stops(tmp_path: Path) -> None:
    tools = _tools_by_name(tmp_path)
    svg_markup = (
        '<svg width="100" height="100" viewBox="0 0 100 100">'
        '<linearGradient id="g1"><stop offset="0%" stop-color="red"/></linearGradient>'
        '<rect x="0" y="0" width="50" height="50" fill="url(#g1)"/>'
        "</svg>"
    )
    with pytest.raises(ValueError, match="at least two"):
        tools["write_pptx"](path="deck.pptx", content=f"layout: svg\n{svg_markup}\n")


@pytest.mark.real_libreoffice
@pytest.mark.skipif(not _libreoffice_actually_works(), reason="LibreOffice not usable here")
def test_layout_svg_path_and_gradient_survive_libreoffice_conversion(tmp_path: Path) -> None:
    """Real, non-mocked round trip -- catches OOXML corruption from the
    hand-appended <a:cubicBezTo>/<a:quadBezTo>/<a:gradFill> elements that a
    pure structural check could miss."""
    import subprocess

    tools = _tools_by_name(tmp_path)
    svg_markup = (
        '<svg width="800" height="450" viewBox="0 0 800 450">'
        '<defs><linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">'
        '<stop offset="0%" stop-color="#1e3a8a"/>'
        '<stop offset="100%" stop-color="#7c3aed"/></linearGradient>'
        '<radialGradient id="blob"><stop offset="0%" stop-color="#ffffff"/>'
        '<stop offset="100%" stop-color="#f472b6"/></radialGradient></defs>'
        '<rect x="0" y="0" width="800" height="450" fill="url(#bg)"/>'
        '<path d="M100,300 C150,150 350,150 400,300 Q450,400 500,300 L650,300 '
        'L650,380 L100,380 Z" fill="url(#blob)"/>'
        "</svg>"
    )
    tools["write_pptx"](path="deck.pptx", content=f"layout: svg\n{svg_markup}\n")

    result = subprocess.run(
        [
            "soffice",
            "--headless",
            "--convert-to",
            "pdf",
            "--outdir",
            str(tmp_path),
            str(tmp_path / "deck.pptx"),
        ],
        capture_output=True,
        timeout=30,
    )
    assert result.returncode == 0


def test_layout_svg_rejects_malformed_xml(tmp_path: Path) -> None:
    tools = _tools_by_name(tmp_path)
    content = 'layout: svg\n<svg width="100" height="100"><rect></svg>\n'

    with pytest.raises(ValueError, match="not valid XML"):
        tools["write_pptx"](path="deck.pptx", content=content)


def test_layout_mixed_deck_in_one_write_pptx_call(tmp_path: Path) -> None:
    from pptx import Presentation

    tools = _tools_by_name(tmp_path)
    svg_markup = (
        '<svg width="960" height="540" viewBox="0 0 960 540">'
        '<rect x="0" y="0" width="960" height="540" fill="1E2761"/>'
        '<circle cx="120" cy="270" r="40" fill="FF0000"/>'
        '<text x="220" y="260" font-size="36" fill="FFFFFF">Tracking</text>'
        "</svg>"
    )
    content = (
        "# Plain Title\n- a bullet\n"
        "---\n"
        "layout: icon-list\n# Highlights\n- one\n- two\n"
        "---\n"
        "layout: stat-callout\n# Stats\n| Stat | Label |\n| --- | --- |\n| 5 | Five |\n"
        "---\n"
        "layout: two-column\n# Compare\n- left\n>>>\n- right\n"
        "---\n"
        f"layout: svg\n{svg_markup}\n"
    )
    result = tools["write_pptx"](path="deck.pptx", content=content)

    assert result["slide_count"] == 5
    prs = Presentation(str(tmp_path / "deck.pptx"))
    assert check_text_overlaps(prs) == []
    assert check_missing_visual_elements(prs) == [1, 4]
