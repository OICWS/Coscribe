from pathlib import Path

import pytest

from .helpers import (
    _tools_by_name,
)

# --- write_pptx `theme` parameter (deck-wide color/typography identity) ---


def _theme_xml_parts(pptx_path: Path) -> tuple[object, object, object]:
    """(clrScheme element, majorFont element, master) for a saved deck's
    own theme part -- python-pptx has no public API for clrScheme/
    fontScheme (see apply_theme's docstring), so tests read the raw XML
    the same way the implementation writes it."""
    from lxml import etree
    from pptx import Presentation
    from pptx.opc.constants import RELATIONSHIP_TYPE as RT

    prs = Presentation(str(pptx_path))
    master = prs.slide_masters[0]
    theme_part = master.part.part_related_by(RT.THEME)
    root = etree.fromstring(theme_part.blob)
    ns = {"a": "http://schemas.openxmlformats.org/drawingml/2006/main"}
    clr_scheme = root.find(".//a:clrScheme", ns)
    major_font = root.find(".//a:fontScheme/a:majorFont", ns)
    return clr_scheme, major_font, master


def test_theme_token_rejects_malformed_pair(tmp_path: Path) -> None:
    tools = _tools_by_name(tmp_path)
    with pytest.raises(ValueError, match="Malformed theme token"):
        tools["write_pptx"](path="deck.pptx", content="# Title\n- x", theme="bg")


def test_theme_token_rejects_unknown_key(tmp_path: Path) -> None:
    tools = _tools_by_name(tmp_path)
    with pytest.raises(ValueError, match="Unknown theme token"):
        tools["write_pptx"](path="deck.pptx", content="# Title\n- x", theme="foo=bar")


def test_theme_token_rejects_non_hex_color(tmp_path: Path) -> None:
    tools = _tools_by_name(tmp_path)
    with pytest.raises(ValueError, match="6-hex-digit color"):
        tools["write_pptx"](path="deck.pptx", content="# Title\n- x", theme="bg=notacolor")


def test_theme_sets_background_and_clr_scheme_and_font_scheme(tmp_path: Path) -> None:
    """The four color tokens land on the deck's own <a:clrScheme> (not
    just the visible background), and heading_font lands on
    <a:fontScheme>'s majorFont -- so any shape/placeholder that
    references a theme color or inherits the master's font (not just the
    background fill) picks up the new identity too, not only the parts
    of the deck this test can see without reopening the raw XML."""
    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](
        path="deck.pptx",
        content="# Title\n- bullet\n",
        theme="bg=0F172A,text=F8FAFC,surface=1E293B,accent=38BDF8,heading_font=Georgia",
    )

    clr_scheme, major_font, master = _theme_xml_parts(tmp_path / "deck.pptx")
    ns = {"a": "http://schemas.openxmlformats.org/drawingml/2006/main"}

    def scheme_color(tag: str) -> str:
        el = clr_scheme.find(f"a:{tag}", ns).find("a:srgbClr", ns)
        return el.get("val")

    assert scheme_color("lt1") == "0F172A"
    assert scheme_color("dk1") == "F8FAFC"
    assert scheme_color("lt2") == "1E293B"
    assert scheme_color("accent1") == "38BDF8"
    assert scheme_color("hlink") == "38BDF8"
    assert major_font.find("a:latin", ns).get("typeface") == "Georgia"

    from pptx.dml.color import RGBColor

    assert master.background.fill.type is not None
    assert master.background.fill.fore_color.rgb == RGBColor.from_string("0F172A")


def test_no_theme_parameter_leaves_stock_colors_and_plain_background(tmp_path: Path) -> None:
    """Omitting `theme` entirely (the existing, default call shape) must
    change nothing -- no regression for every deck that doesn't opt in."""
    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- bullet\n")

    clr_scheme, _major_font, master = _theme_xml_parts(tmp_path / "deck.pptx")
    ns = {"a": "http://schemas.openxmlformats.org/drawingml/2006/main"}
    assert clr_scheme.find("a:lt1", ns).find("a:sysClr", ns) is not None
    assert clr_scheme.find("a:accent1", ns).find("a:srgbClr", ns).get("val") == "4F81BD"
    assert str(master.background.fill.type) == "BACKGROUND (5)"


def test_icon_list_and_stat_callout_follow_theme_accent_when_unspecified(
    tmp_path: Path,
) -> None:
    """A `layout: icon-list`/`layout: stat-callout` slide with no
    explicit ACCENTHEX in its own directive line must render its accent
    shapes as a theme_color reference (accent1), not a literal color --
    otherwise write_pptx's `theme` parameter would have no visible effect
    on these two prefab layouts at all, repeating the exact "theme
    editing is inert for decorative shapes" gap independently confirmed
    in a competing tool's own output (see PPTX_DESIGN.md)."""
    from pptx import Presentation
    from pptx.enum.dml import MSO_THEME_COLOR
    from pptx.enum.shapes import MSO_SHAPE_TYPE

    tools = _tools_by_name(tmp_path)
    content = (
        "layout: icon-list\n"
        "# Icons\n"
        "- [A] alpha\n"
        "---\n"
        "layout: stat-callout\n"
        "# Stats\n"
        "| Stat | Label |\n"
        "| --- | --- |\n"
        "| 5 | Five |\n"
    )
    tools["write_pptx"](path="deck.pptx", content=content, theme="accent=38BDF8")

    prs = Presentation(str(tmp_path / "deck.pptx"))
    icon = next(s for s in prs.slides[0].shapes if s.shape_type == MSO_SHAPE_TYPE.AUTO_SHAPE)
    assert icon.fill.fore_color.theme_color == MSO_THEME_COLOR.ACCENT_1

    stat_run = next(
        run
        for shape in prs.slides[1].shapes
        if shape.has_text_frame
        for paragraph in shape.text_frame.paragraphs
        for run in paragraph.runs
        if run.text == "5"
    )
    assert stat_run.font.color.theme_color == MSO_THEME_COLOR.ACCENT_1


def test_icon_list_explicit_accent_still_overrides_theme(tmp_path: Path) -> None:
    """A slide's own `layout: icon-list ACCENTHEX` must still win over the
    deck's `theme` accent -- an explicit per-slide override, unchanged
    from before this feature existed."""
    from pptx import Presentation
    from pptx.dml.color import RGBColor
    from pptx.enum.shapes import MSO_SHAPE_TYPE

    tools = _tools_by_name(tmp_path)
    content = "layout: icon-list FF0000\n# Icons\n- [A] alpha\n"
    tools["write_pptx"](path="deck.pptx", content=content, theme="accent=38BDF8")

    prs = Presentation(str(tmp_path / "deck.pptx"))
    icon = next(s for s in prs.slides[0].shapes if s.shape_type == MSO_SHAPE_TYPE.AUTO_SHAPE)
    assert icon.fill.fore_color.rgb == RGBColor.from_string("FF0000")


def test_write_pptx_default_deck_gets_cjk_typeface(tmp_path: Path) -> None:
    """Regression test for a real, diagnosed-but-previously-unfixed bug
    (PPTX_DESIGN.md §3): every stock python-pptx theme ships an empty
    East-Asian typeface, so Chinese/Japanese/Korean text rendered
    unpredictably depending on the opening machine's own font fallback.
    Applies unconditionally, not just when `theme` is given."""
    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# 标题\n- 内容\n")

    _clr_scheme, major_font, _master = _theme_xml_parts(tmp_path / "deck.pptx")
    ns = {"a": "http://schemas.openxmlformats.org/drawingml/2006/main"}
    assert major_font.find("a:ea", ns).get("typeface") == "Microsoft YaHei"


def test_write_pptx_template_path_deck_keeps_its_own_fonts(tmp_path: Path) -> None:
    """The CJK-typeface fix must NOT touch a user-supplied template_path
    file -- silently rewriting fonts in someone's own uploaded/branded
    template would be an unwanted side effect, unlike write_pptx's own
    freshly-created default deck or coscribe's own bundled templates."""
    from lxml import etree
    from pptx import Presentation
    from pptx.opc.constants import RELATIONSHIP_TYPE as RT

    tools = _tools_by_name(tmp_path)
    # Build a template.pptx via write_pptx (gets the CJK fix applied),
    # then blank its ea typeface back out directly via XML -- simulating
    # a real user-authored template that never had one configured, since
    # that's the state this test needs to start from.
    tools["write_pptx"](path="template.pptx", content="# Title\n- bullet\n")
    ns = {"a": "http://schemas.openxmlformats.org/drawingml/2006/main"}
    prs = Presentation(str(tmp_path / "template.pptx"))
    theme_part = prs.slide_masters[0].part.part_related_by(RT.THEME)
    root = etree.fromstring(theme_part.blob)
    root.find(".//a:fontScheme/a:majorFont/a:ea", ns).set("typeface", "")
    theme_part._blob = etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)
    prs.save(str(tmp_path / "template.pptx"))

    tools["write_pptx"](
        path="deck.pptx", content="# Title\n- bullet\n", template_path="template.pptx"
    )
    _clr_scheme, major_font, _master = _theme_xml_parts(tmp_path / "deck.pptx")
    assert major_font.find("a:ea", ns).get("typeface") == ""
