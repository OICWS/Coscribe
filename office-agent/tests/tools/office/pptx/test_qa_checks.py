from pathlib import Path

from coscribe.tools.office.pptx.qa import (
    check_low_contrast,
    check_missing_visual_elements,
    check_text_overlaps,
)


def test_check_missing_visual_elements_ignores_slide_background_color(tmp_path: Path) -> None:
    from pptx import Presentation
    from pptx.dml.color import RGBColor
    from pptx.enum.shapes import MSO_SHAPE
    from pptx.util import Inches

    prs = Presentation()

    # A themed slide (dark background) with only unfilled text boxes --
    # background color alone must not count as a visual element.
    plain_slide = prs.slides.add_slide(prs.slide_layouts[6])
    plain_slide.background.fill.solid()
    plain_slide.background.fill.fore_color.rgb = RGBColor(0x1E, 0x27, 0x61)
    text_box = plain_slide.shapes.add_textbox(Inches(1), Inches(1), Inches(3), Inches(1))
    text_box.text_frame.text = "Just a title, no shapes"

    # A slide with a real colored (filled) shape -- must count.
    decorated_slide = prs.slides.add_slide(prs.slide_layouts[6])
    icon = decorated_slide.shapes.add_shape(
        MSO_SHAPE.OVAL, Inches(1), Inches(1), Inches(0.5), Inches(0.5)
    )
    icon.fill.solid()
    icon.fill.fore_color.rgb = RGBColor(0xFF, 0x00, 0x00)

    assert check_missing_visual_elements(prs) == [1]


def test_check_missing_visual_elements_counts_a_decorative_shape_inherited_from_the_layout(
    tmp_path: Path,
) -> None:
    """Real, hand-authored templates commonly draw decorative background
    art (accent bars, curtain motifs) once on the slide layout/master
    rather than copying it onto every slide -- confirmed live against
    coscribe's own bundled "velis" template, whose curtain-motif graphics
    live as GROUP shapes on the slide master and were false-positively
    flagged as "missing visuals" before _slide_has_visual_element learned
    to also check the slide's own layout and that layout's master."""
    from pptx import Presentation
    from pptx.dml.color import RGBColor
    from pptx.enum.shapes import MSO_SHAPE
    from pptx.util import Inches

    prs = Presentation()
    layout = prs.slide_layouts[6]  # "Blank" -- no shapes of its own by default
    # LayoutShapes has no public add_shape (only SlideShapes does) -- build
    # the shape via a throwaway slide, then move its element onto the
    # layout's own shape tree, matching this module's established
    # "no public API, drop the element directly" idiom (see
    # _remove_placeholder in scripts/build_pptx_templates.py).
    scratch_slide = prs.slides.add_slide(layout)
    decorative = scratch_slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(10), Inches(0.15)
    )
    decorative.fill.solid()
    decorative.fill.fore_color.rgb = RGBColor(0x1E, 0x27, 0x61)
    decorative._element.getparent().remove(decorative._element)  # noqa: SLF001
    layout.shapes._spTree.append(decorative._element)  # noqa: SLF001
    xml_slides = prs.slides._sldIdLst  # noqa: SLF001
    xml_slides.remove(list(xml_slides)[0])

    slide = prs.slides.add_slide(layout)
    text_box = slide.shapes.add_textbox(Inches(1), Inches(1), Inches(3), Inches(1))
    text_box.text_frame.text = "Title only, no shapes of its own"

    assert check_missing_visual_elements(prs) == []


def test_check_low_contrast_flags_light_text_on_a_matching_light_background(
    tmp_path: Path,
) -> None:
    """The common real-world mistake this exists to catch: light gray body
    text on a white/near-white background, both picked from the same
    palette so neither reads as an obvious mistake in isolation."""
    from pptx import Presentation
    from pptx.dml.color import RGBColor
    from pptx.util import Inches, Pt

    prs = Presentation()
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    slide.background.fill.solid()
    slide.background.fill.fore_color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
    box = slide.shapes.add_textbox(Inches(1), Inches(1), Inches(3), Inches(1))
    box.text_frame.text = "Barely readable"
    run = box.text_frame.paragraphs[0].runs[0]
    run.font.color.rgb = RGBColor(0xCC, 0xCC, 0xCC)
    run.font.size = Pt(16)  # ordinary body text -- 4.5:1 threshold applies

    warnings = check_low_contrast(prs)
    assert len(warnings) == 1
    assert warnings[0]["slide"] == 1
    assert warnings[0]["text"] == "Barely readable"
    assert warnings[0]["contrast_ratio"] < 4.5


def test_check_low_contrast_uses_the_looser_ratio_for_large_bold_text(tmp_path: Path) -> None:
    """WCAG's own large-text carve-out (>=18pt, or >=14pt bold, gets 3.0:1
    instead of 4.5:1) -- a color pair that fails the small-text threshold
    (~3.95:1) but clears the large-text one must NOT be flagged for large
    text, and MUST be flagged for the same pair at ordinary body size."""
    from pptx import Presentation
    from pptx.dml.color import RGBColor
    from pptx.util import Inches, Pt

    prs = Presentation()
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    slide.background.fill.solid()
    slide.background.fill.fore_color.rgb = RGBColor(0xFF, 0xFF, 0xFF)

    large = slide.shapes.add_textbox(Inches(1), Inches(1), Inches(3), Inches(1))
    large.text_frame.text = "Large bold headline"
    large_run = large.text_frame.paragraphs[0].runs[0]
    large_run.font.color.rgb = RGBColor(0x80, 0x80, 0x80)  # ~3.95:1
    large_run.font.size = Pt(20)
    large_run.font.bold = True

    small = slide.shapes.add_textbox(Inches(1), Inches(3), Inches(3), Inches(1))
    small.text_frame.text = "Same color, small body text"
    small_run = small.text_frame.paragraphs[0].runs[0]
    small_run.font.color.rgb = RGBColor(0x80, 0x80, 0x80)
    small_run.font.size = Pt(16)

    warnings = check_low_contrast(prs)
    assert [w["text"] for w in warnings] == ["Same color, small body text"]


def test_check_low_contrast_skips_what_it_cannot_resolve(tmp_path: Path) -> None:
    """Deliberately conservative: a gradient-filled background, a
    theme/scheme font color, and a run with no explicit color at all must
    all be silently skipped rather than guessed at -- false positives on
    content this check has no real color data for would erode trust in
    every other (real) hit it reports."""
    from pptx import Presentation
    from pptx.dml.color import RGBColor
    from pptx.enum.dml import MSO_THEME_COLOR
    from pptx.util import Inches, Pt

    prs = Presentation()
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    slide.background.fill.gradient()  # no resolvable solid color anywhere

    gradient_bg_text = slide.shapes.add_textbox(Inches(1), Inches(1), Inches(3), Inches(1))
    gradient_bg_text.text_frame.text = "On a gradient background"
    gradient_run = gradient_bg_text.text_frame.paragraphs[0].runs[0]
    gradient_run.font.color.rgb = RGBColor(0xCC, 0xCC, 0xCC)
    gradient_run.font.size = Pt(16)

    # Give this shape its own solid (white) fill so the background side
    # resolves -- only the font side (a theme color) is under test here.
    scheme_box = slide.shapes.add_textbox(Inches(1), Inches(3), Inches(3), Inches(1))
    scheme_box.fill.solid()
    scheme_box.fill.fore_color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
    scheme_box.text_frame.text = "Theme-colored text"
    scheme_run = scheme_box.text_frame.paragraphs[0].runs[0]
    scheme_run.font.color.theme_color = MSO_THEME_COLOR.ACCENT_1
    scheme_run.font.size = Pt(16)

    assert check_low_contrast(prs) == []


def test_check_low_contrast_resolves_background_from_the_slide_when_shape_has_no_fill(
    tmp_path: Path,
) -> None:
    """A plain textbox (the common case -- write_pptx never fills its own
    text boxes) has to fall back to the slide's own background color, not
    just skip because the shape itself has no fill."""
    from pptx import Presentation
    from pptx.dml.color import RGBColor
    from pptx.util import Inches, Pt

    prs = Presentation()
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    slide.background.fill.solid()
    slide.background.fill.fore_color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
    box = slide.shapes.add_textbox(Inches(1), Inches(1), Inches(3), Inches(1))  # no fill of its own
    box.text_frame.text = "Inherits the slide background"
    run = box.text_frame.paragraphs[0].runs[0]
    run.font.color.rgb = RGBColor(0xCC, 0xCC, 0xCC)
    run.font.size = Pt(16)

    warnings = check_low_contrast(prs)
    assert [w["text"] for w in warnings] == ["Inherits the slide background"]


def test_check_text_overlaps_flags_significantly_overlapping_text_boxes(tmp_path: Path) -> None:
    from pptx import Presentation
    from pptx.util import Inches

    prs = Presentation()
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    subtitle = slide.shapes.add_textbox(Inches(1), Inches(1.5), Inches(4), Inches(0.5))
    subtitle.text_frame.text = "Precision Monitoring at Your Fingertips"
    body = slide.shapes.add_textbox(Inches(1), Inches(1.6), Inches(4), Inches(2))
    body.text_frame.text = "Real-Time Tracking: identify power-hungry appliances instantly."

    warnings = check_text_overlaps(prs)

    assert len(warnings) == 1
    assert warnings[0]["slide"] == 1
    assert "Precision Monitoring" in warnings[0]["text_a"]
    assert "Real-Time Tracking" in warnings[0]["text_b"]


def test_check_text_overlaps_flags_text_overlapping_a_chart(tmp_path: Path) -> None:
    """Real, live-reproduced bug this catches: a chart is a `GraphicFrame`,
    not a text-frame shape, so it was invisible to the text-vs-text-only
    scan even when its own rendered content (axis labels, a chart title)
    visually collided with a nearby placeholder's text -- confirmed via
    add_pptx_chart's own old fixed-position default landing directly on
    top of a slide's body text."""
    from pptx import Presentation
    from pptx.chart.data import CategoryChartData
    from pptx.enum.chart import XL_CHART_TYPE
    from pptx.util import Inches

    prs = Presentation()
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    body = slide.shapes.add_textbox(Inches(1), Inches(1.5), Inches(4), Inches(2))
    body.text_frame.text = "Some real intro text on this slide"

    chart_data = CategoryChartData()  # type: ignore[no-untyped-call]
    chart_data.categories = ["A", "B"]
    chart_data.add_series("S", (1, 2))  # type: ignore[no-untyped-call]
    slide.shapes.add_chart(
        XL_CHART_TYPE.LINE, Inches(1), Inches(1.6), Inches(6), Inches(4), chart_data
    )

    warnings = check_text_overlaps(prs)

    assert len(warnings) == 1
    assert warnings[0]["slide"] == 1
    assert "Some real intro text" in warnings[0]["text_a"]


def test_check_text_overlaps_does_not_flag_a_small_incidental_overlap(tmp_path: Path) -> None:
    from pptx import Presentation
    from pptx.util import Inches

    prs = Presentation()
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    title = slide.shapes.add_textbox(Inches(0.5), Inches(0.5), Inches(6), Inches(1))
    title.text_frame.text = "Title"
    # Body starts just barely inside the title's box -- a sliver of
    # incidental overlap, not a real layout bug.
    body = slide.shapes.add_textbox(Inches(0.5), Inches(1.4), Inches(6), Inches(3))
    body.text_frame.text = "Body content well below the title"

    assert check_text_overlaps(prs) == []


def test_rendered_layout_check_flags_small_body_text_and_sparse_content_slides() -> None:
    """Measured on the render: a deck whose slides pass every structural
    check can still have 10pt text and the lower half of each slide empty."""
    from pptx import Presentation
    from pptx.util import Inches

    from coscribe.tools.office.pptx.qa import check_rendered_layout

    prs = Presentation()
    for _ in range(3):
        prs.slides.add_slide(prs.slide_layouts[6])

    def page(title_h: float, body_h: float, body_bottom: float) -> dict[str, object]:
        # 540pt tall page; a title, then eight body words ending at body_bottom.
        words = [(50.0, 20.0, 400.0, 20.0 + title_h)]
        words += [
            (50.0 + i * 40, body_bottom - body_h, 85.0 + i * 40, body_bottom) for i in range(8)
        ]
        return {"width": 960.0, "height": 540.0, "words": words}

    layout = [
        page(40, 20, 400),  # cover: never "sparse"
        page(40, 14.4, 150),  # 12pt body, content ends at 28%
        page(40, 28, 480),  # 23pt body, fills the slide
    ]
    small, sparse = check_rendered_layout(layout, prs)

    assert small == [{"slide": 2, "body_text_pt": 12.0}]
    assert [s["slide"] for s in sparse] == [2]
    assert sparse[0]["content_ends_at_pct"] == 28

    # A chart reaching the lower half makes a slide with little text not sparse.
    from pptx.chart.data import CategoryChartData
    from pptx.enum.chart import XL_CHART_TYPE

    data = CategoryChartData()
    data.categories = ["a", "b"]
    data.add_series("s", (1, 2))
    prs.slides[1].shapes.add_chart(
        XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(1), Inches(3), Inches(6), Inches(3.5), data
    )
    _, sparse_with_chart = check_rendered_layout(layout, prs)
    assert sparse_with_chart == []
