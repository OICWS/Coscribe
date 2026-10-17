import zipfile
from pathlib import Path

import pytest

from coscribe.tools.presentations import build_presentation_tools

from .helpers import (
    _libreoffice_actually_works,
    _tools_by_name,
)

# --- add_pptx_formula (native OMML equations, vendored LaTeX->OMML compiler) ---


def test_add_pptx_formula_adds_a_block_equation(tmp_path: Path) -> None:
    from lxml import etree
    from pptx import Presentation

    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- bullet")

    result = tools["add_pptx_formula"](
        path="deck.pptx",
        slide=1,
        latex=r"\frac{-b \pm \sqrt{b^2-4ac}}{2a}",
        left_in=1.0,
        top_in=2.0,
        width_in=5.0,
        height_in=1.5,
    )

    prs = Presentation(tmp_path / "deck.pptx")
    shape = list(prs.slides[0].shapes)[result["shape_index"]]
    assert shape.left == 914400
    assert shape.width == 4572000
    p_element = shape.text_frame.paragraphs[0]._p  # noqa: SLF001
    xml = etree.tostring(p_element).decode()
    assert "{http://schemas.microsoft.com/office/drawing/2010/main}m" in [
        child.tag for child in p_element
    ]
    assert "oMathPara" in xml  # display=True -> block equation, centered
    assert "√" not in xml  # real OMML radical markup, not a unicode glyph
    assert result["display"] is True


def test_add_pptx_formula_display_false_is_inline_not_wrapped_in_omathpara(
    tmp_path: Path,
) -> None:
    from lxml import etree
    from pptx import Presentation

    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- bullet")

    result = tools["add_pptx_formula"](
        path="deck.pptx",
        slide=1,
        latex=r"x_i^2 + y_i^2 = r^2",
        left_in=1.0,
        top_in=4.0,
        width_in=3.0,
        height_in=0.6,
        display=False,
    )

    prs = Presentation(tmp_path / "deck.pptx")
    shape = list(prs.slides[0].shapes)[result["shape_index"]]
    p_element = shape.text_frame.paragraphs[0]._p  # noqa: SLF001
    xml = etree.tostring(p_element).decode()
    assert "oMathPara" not in xml  # inline -> bare <m:oMath>, no paragraph wrapper
    assert "oMath" in xml
    assert result["display"] is False


def test_add_pptx_formula_marks_mc_ignorable_a14_on_the_slide(tmp_path: Path) -> None:
    from pptx import Presentation

    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- bullet")
    tools["add_pptx_formula"](
        path="deck.pptx",
        slide=1,
        latex=r"E = mc^2",
        left_in=1.0,
        top_in=1.0,
        width_in=3.0,
        height_in=1.0,
    )

    prs = Presentation(tmp_path / "deck.pptx")
    slide_element = prs.slides[0].element
    mc_ignorable = slide_element.get(
        "{http://schemas.openxmlformats.org/markup-compatibility/2006}Ignorable"
    )
    assert mc_ignorable is not None
    assert "a14" in mc_ignorable.split()
    with zipfile.ZipFile(tmp_path / "deck.pptx") as archive:
        slide_xml = archive.read("ppt/slides/slide1.xml").decode("utf-8")
    assert 'mc:Ignorable="a14"' in slide_xml
    assert "xmlns:ns0=" not in slide_xml


def test_add_pptx_formula_rejects_malformed_latex(tmp_path: Path) -> None:
    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- bullet")

    with pytest.raises(ValueError, match="Could not compile LaTeX formula"):
        tools["add_pptx_formula"](
            path="deck.pptx",
            slide=1,
            latex=r"\frac{1}{",  # unbalanced braces
            left_in=1.0,
            top_in=1.0,
            width_in=3.0,
            height_in=1.0,
        )


@pytest.mark.real_libreoffice
@pytest.mark.skipif(
    not _libreoffice_actually_works(),
    reason="LibreOffice not installed or not functional in this environment",
)
def test_add_pptx_formula_renders_through_libreoffice_without_qa_skip(tmp_path: Path) -> None:
    """Not a rendering-correctness assertion (that needs a human eye on a
    PNG, done manually during implementation -- see PPTX_DESIGN.md) --
    just confirms the file this tool produces isn't one LibreOffice itself
    refuses to convert (the class of defect a broken OOXML write causes)."""
    state_dir = tmp_path / "state"
    tools = {
        tool.__name__: tool
        for tool in build_presentation_tools(tmp_path / "workspace", state_dir=state_dir)  # type: ignore[attr-defined]
    }
    tools["write_pptx"](path="deck.pptx", content="# Title\n- bullet")
    tools["add_pptx_formula"](
        path="deck.pptx",
        slide=1,
        latex=r"\sum_{i=1}^{n} i = \frac{n(n+1)}{2}",
        left_in=1.0,
        top_in=1.0,
        width_in=5.0,
        height_in=1.0,
    )

    result = tools["render_pptx_preview"](path="deck.pptx")
    assert result["preview_skipped_reason"] is None
    assert len(result["preview_paths"]) == 1


def test_add_pptx_formula_is_write_local_and_gated(tmp_path: Path) -> None:
    from coscribe.runtime import get_tool_metadata

    tools = _tools_by_name(tmp_path)
    metadata = get_tool_metadata(tools["add_pptx_formula"])
    assert metadata.risk_category == "WRITE_LOCAL"
    assert metadata.requires_approval is True
