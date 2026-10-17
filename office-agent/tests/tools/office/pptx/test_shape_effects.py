from pathlib import Path

import pytest

from .helpers import (
    _libreoffice_actually_works,
    _tools_by_name,
)


def _add_test_shape(tools: dict, tmp_path: Path) -> int:
    result = tools["add_pptx_shape"](
        path="deck.pptx",
        slide=1,
        shape_type="RECTANGLE",
        left_in=1.0,
        top_in=1.0,
        width_in=2.0,
        height_in=1.0,
    )
    return result["shape_index"]


def test_add_pptx_shape_effect_shadow_builds_outer_shdw(tmp_path: Path) -> None:
    from pptx import Presentation
    from pptx.oxml.ns import qn

    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- body")
    shape_index = _add_test_shape(tools, tmp_path)

    tools["add_pptx_shape_effect"](
        path="deck.pptx",
        slide=1,
        shape_index=shape_index,
        effect="shadow",
        color="FF0000",
        opacity=0.5,
        size_pt=6.0,
        distance_pt=3.0,
        direction=90.0,
    )

    prs = Presentation(tmp_path / "deck.pptx")
    shape = list(prs.slides[0].shapes)[shape_index]
    effect_lst = shape._element.spPr.find(qn("a:effectLst"))
    assert effect_lst is not None
    outer_shdw = effect_lst.find(qn("a:outerShdw"))
    assert outer_shdw is not None
    assert outer_shdw.get("blurRad") == str(6 * 12700)
    assert outer_shdw.get("dist") == str(3 * 12700)
    assert outer_shdw.get("dir") == str(90 * 60000)
    srgb_clr = outer_shdw.find(qn("a:srgbClr"))
    assert srgb_clr.get("val") == "FF0000"
    assert srgb_clr.find(qn("a:alpha")).get("val") == "50000"


def test_add_pptx_shape_effect_glow_builds_glow_element(tmp_path: Path) -> None:
    from pptx import Presentation
    from pptx.oxml.ns import qn

    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- body")
    shape_index = _add_test_shape(tools, tmp_path)

    tools["add_pptx_shape_effect"](
        path="deck.pptx",
        slide=1,
        shape_index=shape_index,
        effect="glow",
        color="00FF00",
        opacity=0.6,
        size_pt=10.0,
    )

    prs = Presentation(tmp_path / "deck.pptx")
    shape = list(prs.slides[0].shapes)[shape_index]
    effect_lst = shape._element.spPr.find(qn("a:effectLst"))
    glow = effect_lst.find(qn("a:glow"))
    assert glow is not None
    assert glow.get("rad") == str(10 * 12700)
    srgb_clr = glow.find(qn("a:srgbClr"))
    assert srgb_clr.get("val") == "00FF00"
    assert srgb_clr.find(qn("a:alpha")).get("val") == "60000"


def test_add_pptx_shape_effect_soft_edge_builds_soft_edge_element(tmp_path: Path) -> None:
    from pptx import Presentation
    from pptx.oxml.ns import qn

    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- body")
    shape_index = _add_test_shape(tools, tmp_path)

    tools["add_pptx_shape_effect"](
        path="deck.pptx", slide=1, shape_index=shape_index, effect="soft_edge", size_pt=5.0
    )

    prs = Presentation(tmp_path / "deck.pptx")
    shape = list(prs.slides[0].shapes)[shape_index]
    effect_lst = shape._element.spPr.find(qn("a:effectLst"))
    soft_edge = effect_lst.find(qn("a:softEdge"))
    assert soft_edge is not None
    assert soft_edge.get("rad") == str(5 * 12700)
    # softEdge carries no color -- confirm no stray srgbClr sibling.
    assert soft_edge.find(qn("a:srgbClr")) is None


def test_add_pptx_shape_effect_composes_across_calls_in_schema_order(tmp_path: Path) -> None:
    """CT_EffectList's own fixed child order is glow, outerShdw, softEdge
    (among the three this tool supports) -- applying them in reverse call
    order must still land in that order in the XML, and all three must
    coexist (this tool doesn't clobber a different effect type)."""
    from pptx import Presentation
    from pptx.oxml.ns import qn

    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- body")
    shape_index = _add_test_shape(tools, tmp_path)

    tools["add_pptx_shape_effect"](
        path="deck.pptx", slide=1, shape_index=shape_index, effect="soft_edge", size_pt=4.0
    )
    tools["add_pptx_shape_effect"](
        path="deck.pptx", slide=1, shape_index=shape_index, effect="shadow"
    )
    tools["add_pptx_shape_effect"](
        path="deck.pptx", slide=1, shape_index=shape_index, effect="glow"
    )

    prs = Presentation(tmp_path / "deck.pptx")
    shape = list(prs.slides[0].shapes)[shape_index]
    effect_lst = shape._element.spPr.find(qn("a:effectLst"))
    tags = [c.tag for c in effect_lst]
    assert tags == [qn("a:glow"), qn("a:outerShdw"), qn("a:softEdge")]


def test_add_pptx_shape_effect_same_type_replaces_in_place(tmp_path: Path) -> None:
    from pptx import Presentation
    from pptx.oxml.ns import qn

    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- body")
    shape_index = _add_test_shape(tools, tmp_path)

    tools["add_pptx_shape_effect"](
        path="deck.pptx", slide=1, shape_index=shape_index, effect="shadow", color="000000"
    )
    tools["add_pptx_shape_effect"](
        path="deck.pptx", slide=1, shape_index=shape_index, effect="shadow", color="0000FF"
    )

    prs = Presentation(tmp_path / "deck.pptx")
    shape = list(prs.slides[0].shapes)[shape_index]
    effect_lst = shape._element.spPr.find(qn("a:effectLst"))
    outer_shdws = effect_lst.findall(qn("a:outerShdw"))
    assert len(outer_shdws) == 1
    assert outer_shdws[0].find(qn("a:srgbClr")).get("val") == "0000FF"


def test_add_pptx_shape_effect_none_clears_all_managed_effects(tmp_path: Path) -> None:
    from pptx import Presentation
    from pptx.oxml.ns import qn

    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- body")
    shape_index = _add_test_shape(tools, tmp_path)

    tools["add_pptx_shape_effect"](
        path="deck.pptx", slide=1, shape_index=shape_index, effect="shadow"
    )
    tools["add_pptx_shape_effect"](
        path="deck.pptx", slide=1, shape_index=shape_index, effect="glow"
    )
    tools["add_pptx_shape_effect"](
        path="deck.pptx", slide=1, shape_index=shape_index, effect="none"
    )

    prs = Presentation(tmp_path / "deck.pptx")
    shape = list(prs.slides[0].shapes)[shape_index]
    effect_lst = shape._element.spPr.find(qn("a:effectLst"))
    assert effect_lst is not None
    assert len(list(effect_lst)) == 0


def test_add_pptx_shape_effect_works_on_a_picture_shape(tmp_path: Path) -> None:
    from pptx import Presentation
    from pptx.oxml.ns import qn

    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- body")
    tools["add_pptx_icon"](path="deck.pptx", slide=1, icon_name="star", left_in=1, top_in=1)
    shapes = tools["list_pptx_shapes"](path="deck.pptx", slide=1)
    shape_index = len(shapes["shapes"]) - 1

    tools["add_pptx_shape_effect"](
        path="deck.pptx", slide=1, shape_index=shape_index, effect="glow", color="00A2FF"
    )

    prs = Presentation(tmp_path / "deck.pptx")
    shape = list(prs.slides[0].shapes)[shape_index]
    effect_lst = shape._element.spPr.find(qn("a:effectLst"))
    assert effect_lst.find(qn("a:glow")) is not None


def test_add_pptx_shape_effect_rejects_unknown_effect_name(tmp_path: Path) -> None:
    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- body")
    shape_index = _add_test_shape(tools, tmp_path)

    with pytest.raises(ValueError, match="effect"):
        tools["add_pptx_shape_effect"](
            path="deck.pptx", slide=1, shape_index=shape_index, effect="bogus"
        )


def test_add_pptx_shape_effect_rejects_bad_color(tmp_path: Path) -> None:
    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- body")
    shape_index = _add_test_shape(tools, tmp_path)

    with pytest.raises(ValueError, match="color"):
        tools["add_pptx_shape_effect"](
            path="deck.pptx", slide=1, shape_index=shape_index, effect="shadow", color="zzzzzz"
        )


def test_add_pptx_shape_effect_rejects_opacity_out_of_range(tmp_path: Path) -> None:
    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- body")
    shape_index = _add_test_shape(tools, tmp_path)

    with pytest.raises(ValueError, match="opacity"):
        tools["add_pptx_shape_effect"](
            path="deck.pptx", slide=1, shape_index=shape_index, effect="glow", opacity=1.5
        )


def test_add_pptx_shape_effect_rejects_non_positive_size(tmp_path: Path) -> None:
    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- body")
    shape_index = _add_test_shape(tools, tmp_path)

    with pytest.raises(ValueError, match="size_pt"):
        tools["add_pptx_shape_effect"](
            path="deck.pptx", slide=1, shape_index=shape_index, effect="glow", size_pt=0
        )


def test_add_pptx_shape_effect_rejects_out_of_range_shape_index(tmp_path: Path) -> None:
    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- body")

    with pytest.raises(ValueError, match="shape_index"):
        tools["add_pptx_shape_effect"](path="deck.pptx", slide=1, shape_index=99, effect="shadow")


def test_add_pptx_shape_effect_is_medium_risk_and_requires_approval(tmp_path: Path) -> None:
    from coscribe.runtime import get_tool_metadata

    tools = _tools_by_name(tmp_path)
    metadata = get_tool_metadata(tools["add_pptx_shape_effect"])
    assert metadata.risk_category == "WRITE_LOCAL"
    assert metadata.requires_approval is True


@pytest.mark.real_libreoffice
@pytest.mark.skipif(not _libreoffice_actually_works(), reason="LibreOffice not usable here")
def test_add_pptx_shape_effect_survives_libreoffice_conversion(tmp_path: Path) -> None:
    """Real, non-mocked round trip -- catches OOXML corruption from the
    hand-built <a:outerShdw>/<a:glow>/<a:softEdge> elements that a pure
    structural check could miss."""
    import subprocess

    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- body")
    shape_index = _add_test_shape(tools, tmp_path)
    tools["add_pptx_shape_effect"](
        path="deck.pptx", slide=1, shape_index=shape_index, effect="shadow"
    )
    tools["add_pptx_shape_effect"](
        path="deck.pptx", slide=1, shape_index=shape_index, effect="glow"
    )

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
    assert (tmp_path / "deck.pdf").is_file()
    assert (tmp_path / "deck.pdf").stat().st_size > 0
