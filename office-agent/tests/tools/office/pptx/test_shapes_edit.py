from pathlib import Path

import pytest

from tests.pptx_fixtures import write_smartart_fixture as _write_smartart_fixture

from .helpers import (
    _tools_by_name,
)

# --- list_pptx_shapes / edit_pptx_shape (Tier 1: editing an existing deck) ---


def test_list_pptx_shapes_describes_icon_list_shapes(tmp_path: Path) -> None:
    tools = _tools_by_name(tmp_path)
    content = "layout: icon-list FF0000\n# Icons\n- [A] alpha\n- [B] beta\n"
    tools["write_pptx"](path="deck.pptx", content=content)

    result = tools["list_pptx_shapes"](path="deck.pptx", slide=1)
    assert result["slide"] == 1
    shapes = result["shapes"]
    assert result["shape_count"] == len(shapes) == 5

    title = shapes[0]
    assert title["is_placeholder"] is True
    assert title["text_preview"] == "Icons"

    icon_a = shapes[1]
    assert icon_a["text_preview"] == "A"
    assert icon_a["fill"] == "#FF0000"
    assert icon_a["is_table"] is False
    assert isinstance(icon_a["left_in"], float)
    assert isinstance(icon_a["rotation"], float)


def test_list_pptx_shapes_reports_table_dimensions(tmp_path: Path) -> None:
    tools = _tools_by_name(tmp_path)
    content = "# Table\n| A | B | C |\n| --- | --- | --- |\n| 1 | 2 | 3 |\n"
    tools["write_pptx"](path="deck.pptx", content=content)

    result = tools["list_pptx_shapes"](path="deck.pptx", slide=1)
    table_shape = next(s for s in result["shapes"] if s["is_table"])
    assert table_shape["table_dimensions"] == {"rows": 2, "cols": 3}
    assert table_shape["fill"] is None  # GraphicFrame has no .fill at all


def test_list_pptx_shapes_theme_color_fill_reports_theme_reference(tmp_path: Path) -> None:
    """An icon-list slide with no explicit accent (follows the deck's
    theme accent1, see write_pptx's `theme` parameter) must report its
    fill as a "theme:" reference, not try (and fail) to resolve it to a
    literal RGB -- a SchemeColor has no .rgb property at all."""
    tools = _tools_by_name(tmp_path)
    content = "layout: icon-list\n# Icons\n- [A] alpha\n"
    tools["write_pptx"](path="deck.pptx", content=content)

    result = tools["list_pptx_shapes"](path="deck.pptx", slide=1)
    icon = next(s for s in result["shapes"] if s["text_preview"] == "A")
    assert icon["fill"] == "theme:ACCENT_1"


def test_list_pptx_shapes_rejects_out_of_range_slide(tmp_path: Path) -> None:
    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- bullet\n")
    with pytest.raises(ValueError, match="out of range"):
        tools["list_pptx_shapes"](path="deck.pptx", slide=2)


# --- SmartArt detection/extraction + delete_pptx_shape ---
#
# python-pptx has no SmartArt-creation API at all (and neither does any
# other library -- the layout algorithm lives in PowerPoint itself, not
# the file format), so there's no way to build a real SmartArt-bearing
# .pptx through python-pptx's own object model the way every other
# fixture in this file is built. `write_smartart_fixture` (in
# `pptx_fixtures.py`, shared with the golden tests) instead
# hand-writes the real OOXML structure directly into a python-pptx-saved
# file's zip package -- the exact <a:graphicData uri=".../diagram">/
# <dgm:relIds r:dm=.../<dgm:pt>/<dgm:t> shape cross-checked against two
# independent, real, working OOXML-consuming implementations (Apache
# POI's XSLFDiagram, LibreOffice's oox diagram filter -- see this
# module's own _SMARTART_NS comment), not guessed.


def test_list_pptx_shapes_detects_smartart_and_extracts_node_text(tmp_path: Path) -> None:
    tools = _tools_by_name(tmp_path)
    _write_smartart_fixture(tmp_path / "smartart.pptx")

    shapes = tools["list_pptx_shapes"](path="smartart.pptx", slide=1)["shapes"]
    assert len(shapes) == 1
    assert shapes[0]["is_smartart"] is True
    assert shapes[0]["smartart_text"] == ["Plan", "Build phase", "Ship"]


def test_list_pptx_shapes_non_smartart_shape_reports_false_and_none(tmp_path: Path) -> None:
    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- bullet\n")

    shapes = tools["list_pptx_shapes"](path="deck.pptx", slide=1)["shapes"]
    for shape in shapes:
        assert shape["is_smartart"] is False
        assert shape["smartart_text"] is None


def test_delete_pptx_shape_removes_smartart_and_survives_round_trip(tmp_path: Path) -> None:
    import warnings

    from pptx import Presentation

    tools = _tools_by_name(tmp_path)
    _write_smartart_fixture(tmp_path / "smartart.pptx")

    result = tools["delete_pptx_shape"](path="smartart.pptx", slide=1, shape_index=0)
    assert result == {"path": "smartart.pptx", "slide": 1, "shape_index": 0}

    with warnings.catch_warnings():
        warnings.simplefilter("error")
        prs = Presentation(str(tmp_path / "smartart.pptx"))
    assert list(prs.slides[0].shapes) == []


# --- read_pptx_xml / edit_pptx_xml -- the generic OOXML escape hatch ---


def test_read_pptx_xml_smartart_auto_returns_the_linked_data_part(tmp_path: Path) -> None:
    tools = _tools_by_name(tmp_path)
    _write_smartart_fixture(tmp_path / "smartart.pptx")

    result = tools["read_pptx_xml"](path="smartart.pptx", slide=1, shape_index=0)

    assert result["source"] == "smartart_data"
    assert "Plan" in result["xml"]
    assert "Build" in result["xml"]
    assert "Ship" in result["xml"]


def test_read_pptx_xml_smartart_part_shape_returns_the_graphicframe_wrapper(
    tmp_path: Path,
) -> None:
    tools = _tools_by_name(tmp_path)
    _write_smartart_fixture(tmp_path / "smartart.pptx")

    result = tools["read_pptx_xml"](path="smartart.pptx", slide=1, shape_index=0, part="shape")

    assert result["source"] == "shape"
    assert "graphicFrame" in result["xml"]
    # The real node text lives in the linked data part, not here.
    assert "Plan" not in result["xml"]


def test_read_pptx_xml_non_smartart_shape_returns_its_own_inline_xml(tmp_path: Path) -> None:
    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Real Title\n- a bullet\n")

    result = tools["read_pptx_xml"](path="deck.pptx", slide=1, shape_index=0)

    assert result["source"] == "shape"
    assert "Real Title" in result["xml"]


def test_read_pptx_xml_smartart_data_part_on_a_non_smartart_shape_raises(tmp_path: Path) -> None:
    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- bullet\n")

    with pytest.raises(ValueError, match="isn't SmartArt"):
        tools["read_pptx_xml"](path="deck.pptx", slide=1, shape_index=0, part="smartart_data")


def test_read_pptx_xml_rejects_an_invalid_part_argument(tmp_path: Path) -> None:
    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- bullet\n")

    with pytest.raises(ValueError, match='"auto", "shape", or "smartart_data"'):
        tools["read_pptx_xml"](path="deck.pptx", slide=1, shape_index=0, part="bogus")


def test_edit_pptx_xml_smartart_node_text_persists_and_round_trips(tmp_path: Path) -> None:
    tools = _tools_by_name(tmp_path)
    _write_smartart_fixture(tmp_path / "smartart.pptx")

    result = tools["edit_pptx_xml"](
        path="smartart.pptx",
        slide=1,
        shape_index=0,
        xpath=".//dgm:t[.//a:t='Plan']//a:t",
        new_text="PLANNED START",
    )
    assert result == {
        "path": "smartart.pptx",
        "slide": 1,
        "shape_index": 0,
        "source": "smartart_data",
    }

    # Read back through the same path a real conversation would use --
    # list_pptx_shapes' own smartart_text, not a re-parse of internals.
    shapes = tools["list_pptx_shapes"](path="smartart.pptx", slide=1)["shapes"]
    assert shapes[0]["smartart_text"] == ["PLANNED START", "Build phase", "Ship"]


def test_edit_pptx_xml_only_touches_the_targeted_shape_not_a_sibling(tmp_path: Path) -> None:
    """Regression test for a real bug caught before it shipped: `//foo` in
    XPath means "search the whole document this node belongs to", not
    "search this node's own descendants" -- calling `.xpath("//a:t")`
    directly on a live shape element (which lives inside the full
    <p:sld> tree alongside every other shape) would match a *sibling*
    shape's text too. Here, shape_index=0's own text is "Real Title" and
    shape_index=1's is "a bullet" -- each unique across the whole slide.
    Asking to edit shape_index=0 with an xpath that only matches text
    actually inside shape_index=1 must find *nothing* (proving the
    search was correctly scoped to shape 0 alone), not silently succeed
    against the wrong shape."""
    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Real Title\n- a bullet\n")

    with pytest.raises(ValueError, match="matched 0 element"):
        tools["edit_pptx_xml"](
            path="deck.pptx",
            slide=1,
            shape_index=0,
            xpath=".//a:t[.='a bullet']",
            new_text="hijacked",
        )

    # The sibling shape's real text must be completely untouched.
    shapes = tools["list_pptx_shapes"](path="deck.pptx", slide=1)["shapes"]
    assert shapes[1]["text_preview"] == "a bullet"


def test_edit_pptx_xml_shape_text_persists_and_stays_schema_valid(tmp_path: Path) -> None:
    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Real Title\n- a bullet\n")

    result = tools["edit_pptx_xml"](
        path="deck.pptx", slide=1, shape_index=0, xpath=".//a:t", new_text="Edited Title"
    )
    assert result == {"path": "deck.pptx", "slide": 1, "shape_index": 0, "source": "shape"}

    shapes = tools["list_pptx_shapes"](path="deck.pptx", slide=1)["shapes"]
    assert shapes[0]["text_preview"] == "Edited Title"


def test_edit_pptx_xml_preserves_shape_order(tmp_path: Path) -> None:
    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Real Title\n- a bullet\n")
    before = tools["list_pptx_shapes"](path="deck.pptx", slide=1)["shapes"]

    tools["edit_pptx_xml"](
        path="deck.pptx", slide=1, shape_index=1, xpath=".//a:t", new_text="Edited bullet"
    )

    after = tools["list_pptx_shapes"](path="deck.pptx", slide=1)["shapes"]
    assert len(after) == len(before)
    assert after[0]["text_preview"] == before[0]["text_preview"]
    assert after[1]["text_preview"] == "Edited bullet"


def test_edit_pptx_xml_set_attributes_persists_a_real_attribute_change(tmp_path: Path) -> None:
    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Real Title\n- a bullet\n")

    tools["edit_pptx_xml"](
        path="deck.pptx",
        slide=1,
        shape_index=1,
        xpath=".//p:cNvPr",
        set_attributes="name=My Custom Shape Name",
    )

    result = tools["read_pptx_xml"](path="deck.pptx", slide=1, shape_index=1)
    assert 'name="My Custom Shape Name"' in result["xml"]


def test_edit_pptx_xml_set_attributes_parses_multiple_lines(tmp_path: Path) -> None:
    tools = _tools_by_name(tmp_path)
    _write_smartart_fixture(tmp_path / "smartart.pptx")

    tools["edit_pptx_xml"](
        path="smartart.pptx",
        slide=1,
        shape_index=0,
        xpath=".//dgm:pt[@modelId='11']",
        set_attributes="type=sibTrans\ncxnId=y",
    )

    result = tools["read_pptx_xml"](path="smartart.pptx", slide=1, shape_index=0)
    assert 'type="sibTrans"' in result["xml"]
    assert 'cxnId="y"' in result["xml"]


def test_edit_pptx_xml_set_attributes_rejects_a_line_with_no_equals_sign(
    tmp_path: Path,
) -> None:
    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Real Title\n- a bullet\n")

    with pytest.raises(ValueError, match="has no '='"):
        tools["edit_pptx_xml"](
            path="deck.pptx",
            slide=1,
            shape_index=1,
            xpath=".//p:cNvPr",
            set_attributes="not-a-valid-line",
        )


def test_edit_pptx_xml_rejects_invalid_ooxml_without_touching_the_file(tmp_path: Path) -> None:
    """A real schema-rejected edit -- `bookmarkId` isn't an allowed
    attribute on `<p:sp>` (confirmed by the real ECMA-376 Transitional
    schema this file already vendors) -- proves assert_ooxml_valid is
    genuinely wired into edit_pptx_xml's write path, same guarantee every
    other hand-XML tool in this module makes: an invalid result means the
    file was never modified."""
    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Real Title\n- a bullet\n")
    before = tools["read_pptx_xml"](path="deck.pptx", slide=1, shape_index=0)["xml"]

    with pytest.raises(RuntimeError, match="failed schema validation"):
        tools["edit_pptx_xml"](
            path="deck.pptx",
            slide=1,
            shape_index=0,
            xpath=".",
            set_attributes="a:bookmarkId=coscribe-test",
        )

    after = tools["read_pptx_xml"](path="deck.pptx", slide=1, shape_index=0)["xml"]
    assert after == before


def test_edit_pptx_xml_requires_new_text_or_set_attributes(tmp_path: Path) -> None:
    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Real Title\n- a bullet\n")

    with pytest.raises(ValueError, match="nothing to change"):
        tools["edit_pptx_xml"](path="deck.pptx", slide=1, shape_index=0, xpath=".//a:t")


def test_edit_pptx_xml_rejects_an_ambiguous_match(tmp_path: Path) -> None:
    tools = _tools_by_name(tmp_path)
    _write_smartart_fixture(tmp_path / "smartart.pptx")

    with pytest.raises(ValueError, match="matched 10 element"):
        tools["edit_pptx_xml"](
            path="smartart.pptx", slide=1, shape_index=0, xpath=".//dgm:pt", new_text="x"
        )


def test_edit_pptx_xml_rejects_a_non_element_match(tmp_path: Path) -> None:
    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Real Title\n- a bullet\n")

    with pytest.raises(ValueError, match="not an element"):
        tools["edit_pptx_xml"](
            path="deck.pptx", slide=1, shape_index=0, xpath=".//a:t/text()", new_text="x"
        )


def test_edit_pptx_xml_smartart_data_requires_a_smartart_shape(tmp_path: Path) -> None:
    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- bullet\n")

    with pytest.raises(ValueError, match="isn't SmartArt"):
        tools["edit_pptx_xml"](
            path="deck.pptx",
            slide=1,
            shape_index=0,
            xpath=".",
            new_text="x",
            part="smartart_data",
        )


def test_delete_pptx_shape_removes_only_that_shape(tmp_path: Path) -> None:
    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- bullet\n")
    before = tools["list_pptx_shapes"](path="deck.pptx", slide=1)["shapes"]

    tools["delete_pptx_shape"](path="deck.pptx", slide=1, shape_index=1)

    after = tools["list_pptx_shapes"](path="deck.pptx", slide=1)["shapes"]
    assert len(after) == len(before) - 1
    assert after[0]["index"] == 0
    assert after[0]["text_preview"] == before[0]["text_preview"]


def test_delete_pptx_shape_rejects_out_of_range_shape_index(tmp_path: Path) -> None:
    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- bullet\n")

    with pytest.raises(ValueError, match="2 shape"):
        tools["delete_pptx_shape"](path="deck.pptx", slide=1, shape_index=99)


def test_delete_pptx_shape_is_medium_risk_and_requires_approval(tmp_path: Path) -> None:
    from coscribe.runtime import get_tool_metadata

    tools = _tools_by_name(tmp_path)
    metadata = get_tool_metadata(tools["delete_pptx_shape"])
    assert metadata.risk_category == "WRITE_LOCAL"
    assert metadata.requires_approval is True


def test_edit_pptx_shape_changes_geometry_rotation_and_fill(tmp_path: Path) -> None:
    from pptx import Presentation
    from pptx.dml.color import RGBColor
    from pptx.util import Emu, Inches

    tools = _tools_by_name(tmp_path)
    content = "layout: icon-list FF0000\n# Icons\n- [A] alpha\n"
    tools["write_pptx"](path="deck.pptx", content=content)

    result = tools["edit_pptx_shape"](
        path="deck.pptx",
        slide=1,
        shape_index=1,
        left_in=2.0,
        top_in=3.0,
        width_in=1.5,
        height_in=1.5,
        rotation=45.0,
        fill_color="00FF00",
    )
    assert result["shape"]["left_in"] == 2.0
    assert result["shape"]["rotation"] == 45.0
    assert result["shape"]["fill"] == "#00FF00"

    prs = Presentation(str(tmp_path / "deck.pptx"))
    icon = list(prs.slides[0].shapes)[1]
    assert icon.left == Inches(2.0)
    assert icon.top == Inches(3.0)
    assert icon.width == Emu(Inches(1.5))
    assert icon.height == Emu(Inches(1.5))
    assert icon.rotation == 45.0
    assert icon.fill.fore_color.rgb == RGBColor.from_string("00FF00")


def test_edit_pptx_shape_partial_update_leaves_other_properties_alone(tmp_path: Path) -> None:
    from pptx import Presentation

    tools = _tools_by_name(tmp_path)
    content = "layout: icon-list FF0000\n# Icons\n- [A] alpha\n"
    tools["write_pptx"](path="deck.pptx", content=content)

    before = tools["list_pptx_shapes"](path="deck.pptx", slide=1)["shapes"][1]
    tools["edit_pptx_shape"](path="deck.pptx", slide=1, shape_index=1, rotation=90.0)

    prs = Presentation(str(tmp_path / "deck.pptx"))
    icon = list(prs.slides[0].shapes)[1]
    assert icon.rotation == 90.0
    assert round(icon.left / 914400, 2) == before["left_in"]
    assert round(icon.top / 914400, 2) == before["top_in"]
    assert str(icon.fill.fore_color.rgb) == "FF0000"  # untouched


def test_edit_pptx_shape_rejects_no_properties_given(tmp_path: Path) -> None:
    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="layout: icon-list\n# Icons\n- [A] alpha\n")
    with pytest.raises(ValueError, match="at least one property"):
        tools["edit_pptx_shape"](path="deck.pptx", slide=1, shape_index=1)


def test_edit_pptx_shape_rejects_bad_fill_color(tmp_path: Path) -> None:
    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="layout: icon-list\n# Icons\n- [A] alpha\n")
    with pytest.raises(ValueError, match="6-hex-digit color"):
        tools["edit_pptx_shape"](path="deck.pptx", slide=1, shape_index=1, fill_color="#00FF00")


def test_edit_pptx_shape_rejects_out_of_range_shape_index(tmp_path: Path) -> None:
    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- bullet\n")
    with pytest.raises(ValueError, match="shape_index"):
        tools["edit_pptx_shape"](path="deck.pptx", slide=1, shape_index=99, rotation=10.0)


def test_edit_pptx_shape_rejects_fill_color_on_a_table(tmp_path: Path) -> None:
    """A table (GraphicFrame) has no .fill attribute at all -- must raise
    a clear error, not an unhandled AttributeError."""
    tools = _tools_by_name(tmp_path)
    content = "# Table\n| A | B |\n| --- | --- |\n| 1 | 2 |\n"
    tools["write_pptx"](path="deck.pptx", content=content)

    shapes = tools["list_pptx_shapes"](path="deck.pptx", slide=1)["shapes"]
    table_index = next(s["index"] for s in shapes if s["is_table"])
    with pytest.raises(ValueError, match="no fill to set"):
        tools["edit_pptx_shape"](
            path="deck.pptx", slide=1, shape_index=table_index, fill_color="00FF00"
        )


def test_edit_pptx_shape_sets_two_color_gradient_fill(tmp_path: Path) -> None:
    from pptx import Presentation
    from pptx.enum.dml import MSO_FILL

    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="layout: icon-list\n# Icons\n- [A] alpha\n")

    tools["edit_pptx_shape"](
        path="deck.pptx", slide=1, shape_index=1, fill_color="0F172A", fill_color_2="38BDF8"
    )

    prs = Presentation(tmp_path / "deck.pptx")
    shape = list(prs.slides[0].shapes)[1]
    assert shape.fill.type == MSO_FILL.GRADIENT
    stops = shape.fill.gradient_stops
    assert str(stops[0].color.rgb) == "0F172A"
    assert str(stops[1].color.rgb) == "38BDF8"


def test_edit_pptx_shape_gradient_angle_applies(tmp_path: Path) -> None:
    from pptx import Presentation

    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="layout: icon-list\n# Icons\n- [A] alpha\n")

    tools["edit_pptx_shape"](
        path="deck.pptx",
        slide=1,
        shape_index=1,
        fill_color="0F172A",
        fill_color_2="38BDF8",
        gradient_angle=45.0,
    )

    prs = Presentation(tmp_path / "deck.pptx")
    shape = list(prs.slides[0].shapes)[1]
    assert shape.fill.gradient_angle == 45.0


def test_edit_pptx_shape_fill_color_2_without_fill_color_raises(tmp_path: Path) -> None:
    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="layout: icon-list\n# Icons\n- [A] alpha\n")
    with pytest.raises(ValueError, match="fill_color_2 needs fill_color"):
        tools["edit_pptx_shape"](path="deck.pptx", slide=1, shape_index=1, fill_color_2="38BDF8")


def test_edit_pptx_shape_gradient_angle_without_fill_color_2_raises(tmp_path: Path) -> None:
    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="layout: icon-list\n# Icons\n- [A] alpha\n")
    with pytest.raises(ValueError, match="gradient_angle only applies"):
        tools["edit_pptx_shape"](
            path="deck.pptx", slide=1, shape_index=1, fill_color="0F172A", gradient_angle=45.0
        )


def test_edit_pptx_shape_sets_text_color_on_title(tmp_path: Path) -> None:
    from pptx import Presentation

    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# **Bold** Title\n- one\n- two")

    tools["edit_pptx_shape"](path="deck.pptx", slide=1, shape_index=0, text_color="2563EB")

    prs = Presentation(tmp_path / "deck.pptx")
    title = prs.slides[0].shapes.title
    for paragraph in title.text_frame.paragraphs:
        for run in paragraph.runs:
            assert str(run.font.color.rgb) == "2563EB"


def test_edit_pptx_shape_text_color_does_not_touch_text_content(tmp_path: Path) -> None:
    from pptx import Presentation

    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- one\n- two")

    tools["edit_pptx_shape"](path="deck.pptx", slide=1, shape_index=0, text_color="2563EB")

    prs = Presentation(tmp_path / "deck.pptx")
    slide = prs.slides[0]
    assert slide.shapes.title.text == "Title"
    text = tools["read_pptx"](path="deck.pptx", slide=1)
    assert "one" in text
    assert "two" in text


def test_edit_pptx_shape_rejects_text_color_on_a_table(tmp_path: Path) -> None:
    tools = _tools_by_name(tmp_path)
    content = "# Table\n| A | B |\n| --- | --- |\n| 1 | 2 |\n"
    tools["write_pptx"](path="deck.pptx", content=content)

    shapes = tools["list_pptx_shapes"](path="deck.pptx", slide=1)["shapes"]
    table_index = next(s["index"] for s in shapes if s["is_table"])
    with pytest.raises(ValueError, match="no text to color"):
        tools["edit_pptx_shape"](
            path="deck.pptx", slide=1, shape_index=table_index, text_color="2563EB"
        )


def test_edit_pptx_shape_rejects_bad_text_color(tmp_path: Path) -> None:
    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- bullet")
    with pytest.raises(ValueError, match="6-hex-digit color"):
        tools["edit_pptx_shape"](path="deck.pptx", slide=1, shape_index=0, text_color="#2563EB")


def test_list_pptx_shapes_describes_gradient_fill(tmp_path: Path) -> None:
    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="layout: icon-list\n# Icons\n- [A] alpha\n")
    tools["edit_pptx_shape"](
        path="deck.pptx", slide=1, shape_index=1, fill_color="0F172A", fill_color_2="38BDF8"
    )

    shapes = tools["list_pptx_shapes"](path="deck.pptx", slide=1)["shapes"]
    fill = shapes[1]["fill"]
    assert fill == {"type": "gradient", "colors": ["#0F172A", "#38BDF8"], "angle": 90.0}
