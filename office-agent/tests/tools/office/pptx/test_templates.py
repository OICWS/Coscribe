import shutil
import zipfile
from pathlib import Path

import pytest

from coscribe.tools.presentations import build_presentation_tools

from .helpers import (
    _tools_by_name,
)


def test_write_pptx_with_template_path_reuses_theme_and_drops_old_slides(
    tmp_path: Path,
) -> None:
    from pptx import Presentation

    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="template.pptx", content="# Old\n- old bullet\n\n---\n\n# Old 2\n- x")

    tools["write_pptx"](
        path="new.pptx", content="# New Title\n- new bullet", template_path="template.pptx"
    )

    text = tools["read_pptx"](path="new.pptx")
    assert "New Title" in text
    assert "new bullet" in text
    assert "Old" not in text

    prs = Presentation(tmp_path / "new.pptx")
    assert len(prs.slides) == 1

    # Re-adding a slide after the template's own slides were cleared must
    # not collide with an orphaned slide part in the zip package.
    import warnings

    with warnings.catch_warnings():
        warnings.simplefilter("error")
        with zipfile.ZipFile(tmp_path / "new.pptx") as archive:
            slide_parts = [n for n in archive.namelist() if n.startswith("ppt/slides/slide")]
    assert len(slide_parts) == 1


def test_write_pptx_with_missing_template_path_raises(tmp_path: Path) -> None:
    tools = _tools_by_name(tmp_path)

    with pytest.raises(ValueError, match="does not exist"):
        tools["write_pptx"](path="new.pptx", content="# Hi\n- x", template_path="missing.pptx")


def test_write_pptx_with_template_missing_required_layouts_raises(tmp_path: Path) -> None:
    from pptx import Presentation
    from pptx.oxml.ns import qn

    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="template.pptx", content="# Old\n- old bullet")

    prs = Presentation(tmp_path / "template.pptx")
    layout_master = prs.slide_masters[0]
    # Strip every layout but the first, simulating a minimal custom template.
    sld_layout_id_lst = layout_master.element.find(qn("p:sldLayoutIdLst"))
    for layout_id in list(sld_layout_id_lst)[1:]:
        r_id = layout_id.get(qn("r:id"))
        layout_master.part.drop_rel(r_id)
        sld_layout_id_lst.remove(layout_id)
    prs.save(tmp_path / "template.pptx")

    with pytest.raises(ValueError, match="slide layout"):
        tools["write_pptx"](path="new.pptx", content="# Hi\n- x", template_path="template.pptx")


# --- fill_pptx_template ---


def _make_fake_template(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    layout_indexes: list[int],
    *,
    template_id: str = "fake",
    add_decorative_shape: bool = False,
    slide_roles: list[str] | None = None,
) -> dict[str, object]:
    """Build a throwaway .pptx with one slide per entry in layout_indexes
    (a python-pptx stock layout index each), optionally add one decorative
    (non-placeholder) shape to slide 1, monkeypatch
    coscribe.tools.office.pptx.template_tools._load_builtin_templates to return exactly
    this one fake TemplateInfo, and return the decorative shape's captured
    (left, top, width, height, fill_rgb) if requested, else {}. `slide_roles`
    defaults to every slide being "content" (the repeatable role) -- tests
    that care about the role-adjustment behavior itself pass an explicit
    list."""
    from pptx import Presentation
    from pptx.dml.color import RGBColor
    from pptx.enum.shapes import MSO_SHAPE

    from coscribe.tools.office.pptx import template_tools as presentations_module
    from coscribe.tools.pptx_templates import TemplateInfo

    prs = Presentation()
    decorative_shape_info: dict[str, object] = {}
    for index, layout_idx in enumerate(layout_indexes):
        slide = prs.slides.add_slide(prs.slide_layouts[layout_idx])
        if index == 0 and add_decorative_shape:
            shape = slide.shapes.add_shape(
                MSO_SHAPE.ROUNDED_RECTANGLE, 100000, 200000, 300000, 400000
            )
            shape.fill.solid()
            shape.fill.fore_color.rgb = RGBColor.from_string("FF00FF")
            decorative_shape_info = {
                "left": shape.left,
                "top": shape.top,
                "width": shape.width,
                "height": shape.height,
                "fill_rgb": str(shape.fill.fore_color.rgb),
            }
    template_path = tmp_path / "fake_template.pptx"
    prs.save(str(template_path))

    info = TemplateInfo(
        id=template_id,
        name="Fake",
        description="fake test template",
        accent="000000",
        slide_count=len(layout_indexes),
        slide_roles=slide_roles if slide_roles is not None else ["content"] * len(layout_indexes),
        dir=tmp_path,
        path=template_path,
        is_widescreen=True,
    )
    monkeypatch.setattr(presentations_module, "_load_builtin_templates", lambda: [info])
    return decorative_shape_info


def test_fill_pptx_template_happy_path_preserves_decorative_shape_and_fills_placeholders(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from pptx import Presentation

    decorative = _make_fake_template(tmp_path, monkeypatch, [1], add_decorative_shape=True)
    tools = _tools_by_name(tmp_path / "workspace")

    tools["fill_pptx_template"](
        path="out.pptx",
        template_id="fake",
        content="# My Title\n- one\n- two",
    )

    prs = Presentation(str(tmp_path / "workspace" / "out.pptx"))
    slide = prs.slides[0]
    assert slide.shapes.title.text == "My Title"
    body = [
        p
        for p in slide.placeholders
        if p.placeholder_format.idx != slide.shapes.title.placeholder_format.idx
    ][0]
    assert [p.text for p in body.text_frame.paragraphs] == ["one", "two"]

    non_placeholder_shapes = [s for s in slide.shapes if not s.is_placeholder]
    assert len(non_placeholder_shapes) == 1
    shape = non_placeholder_shapes[0]
    assert shape.left == decorative["left"]
    assert shape.top == decorative["top"]
    assert shape.width == decorative["width"]
    assert shape.height == decorative["height"]
    assert str(shape.fill.fore_color.rgb) == decorative["fill_rgb"]


def test_leftover_placeholder_warnings_flags_known_patterns() -> None:
    from pptx import Presentation

    from coscribe.tools.office.pptx.qa import leftover_placeholder_warnings

    prs = Presentation()
    cases = [
        "Revenue grew lorem ipsum dolor this quarter",
        "TODO: fill in the real numbers",
        "[insert customer logo here]",
        "xxxxx",
        "This is a placeholder for the chart",
        "Replace this sample text before sending",
    ]
    for text in cases:
        slide = prs.slides.add_slide(prs.slide_layouts[5])
        slide.shapes.title.text = text

    warnings = leftover_placeholder_warnings(prs)
    assert len(warnings) == len(cases)
    assert [w["slide"] for w in warnings] == list(range(1, len(cases) + 1))


def test_leftover_placeholder_warnings_does_not_flag_real_content() -> None:
    from pptx import Presentation

    from coscribe.tools.office.pptx.qa import leftover_placeholder_warnings

    prs = Presentation()
    slide = prs.slides.add_slide(prs.slide_layouts[5])
    slide.shapes.title.text = "How to insert a chart: a sample workflow"

    assert leftover_placeholder_warnings(prs) == []


def test_write_pptx_flags_leftover_todo_in_generated_content(tmp_path: Path) -> None:
    tools = _tools_by_name(tmp_path)

    result = tools["write_pptx"](path="deck.pptx", content="# Title\n- TODO: add real figures")

    assert result["placeholder_warnings"] == [{"slide": 1, "text": "TODO"}]


def test_write_pptx_placeholder_warnings_empty_for_clean_content(tmp_path: Path) -> None:
    tools = _tools_by_name(tmp_path)

    result = tools["write_pptx"](path="deck.pptx", content="# Title\n- real content here")

    assert result["placeholder_warnings"] == []


def test_fill_pptx_template_too_few_chunks_for_fixed_slides_raises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A template with only non-repeatable roles (title + closing, no
    "content") still needs an exact chunk count -- there's nothing to
    duplicate or trim."""
    _make_fake_template(tmp_path, monkeypatch, [1, 1], slide_roles=["title", "closing"])
    tools = _tools_by_name(tmp_path / "workspace")

    with pytest.raises(ValueError, match="needs at least 2 chunk"):
        tools["fill_pptx_template"](
            path="out.pptx", template_id="fake", content="# Only One Chunk\n- x"
        )


def test_fill_pptx_template_repeats_content_slide_when_given_more_chunks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The real point of this feature: a template with one repeatable
    "content" slide accepts more chunks than its own fixed slide count by
    duplicating that slide's design, not by raising."""
    from pptx import Presentation

    _make_fake_template(
        tmp_path, monkeypatch, [1, 1, 1], slide_roles=["title", "content", "closing"]
    )
    tools = _tools_by_name(tmp_path / "workspace")

    content = (
        "# Title\n- t\n---\n# First\n- a\n---\n# Second\n- b\n"
        "---\n# Third\n- c\n---\n# Closing\n- done"
    )
    result = tools["fill_pptx_template"](path="out.pptx", template_id="fake", content=content)
    assert result["slide_count"] == 5

    prs = Presentation(str(tmp_path / "workspace" / "out.pptx"))
    titles = [s.shapes.title.text for s in prs.slides]
    assert titles == ["Title", "First", "Second", "Third", "Closing"]


def test_fill_pptx_template_trims_content_slides_when_given_fewer_chunks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from pptx import Presentation

    _make_fake_template(
        tmp_path,
        monkeypatch,
        [1, 1, 1, 1],
        slide_roles=["title", "content", "content", "closing"],
    )
    tools = _tools_by_name(tmp_path / "workspace")

    content = "# Title\n- t\n---\n# Only One\n- a\n---\n# Closing\n- done"
    result = tools["fill_pptx_template"](path="out.pptx", template_id="fake", content=content)
    assert result["slide_count"] == 3

    prs = Presentation(str(tmp_path / "workspace" / "out.pptx"))
    titles = [s.shapes.title.text for s in prs.slides]
    assert titles == ["Title", "Only One", "Closing"]


def test_fill_pptx_template_zero_content_chunks_drops_all_content_slides(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from pptx import Presentation

    _make_fake_template(
        tmp_path,
        monkeypatch,
        [1, 1, 1, 1],
        slide_roles=["title", "content", "content", "closing"],
    )
    tools = _tools_by_name(tmp_path / "workspace")

    content = "# Title\n- t\n---\n# Closing\n- done"
    result = tools["fill_pptx_template"](path="out.pptx", template_id="fake", content=content)
    assert result["slide_count"] == 2

    prs = Presentation(str(tmp_path / "workspace" / "out.pptx"))
    titles = [s.shapes.title.text for s in prs.slides]
    assert titles == ["Title", "Closing"]


def test_fill_pptx_template_duplicated_content_slide_keeps_decorative_shape(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A duplicated content slide must carry the same decorative
    (non-placeholder) shape the template's own content slide has --
    otherwise "the design scales with content length" would be false for
    anything but the placeholders."""
    from pptx import Presentation

    decorative = _make_fake_template(
        tmp_path,
        monkeypatch,
        [1, 1],
        add_decorative_shape=True,
        slide_roles=["content", "closing"],
    )
    tools = _tools_by_name(tmp_path / "workspace")

    content = "# First\n- a\n---\n# Second\n- b\n---\n# Closing\n- done"
    tools["fill_pptx_template"](path="out.pptx", template_id="fake", content=content)

    prs = Presentation(str(tmp_path / "workspace" / "out.pptx"))
    for slide in (prs.slides[0], prs.slides[1]):
        non_placeholder = [s for s in slide.shapes if not s.is_placeholder]
        assert len(non_placeholder) == 1
        assert str(non_placeholder[0].fill.fore_color.rgb) == decorative["fill_rgb"]


def test_fill_pptx_template_real_bundled_template_grows_and_shrinks(tmp_path: Path) -> None:
    """Integration-level check against a real bundled template (not the
    throwaway fake harness) -- confirms the manifest's actual
    slide_roles round-trips through the real YAML loader correctly."""
    from pptx import Presentation

    tools = _tools_by_name(tmp_path)

    grow_content = (
        "# Title\nSubtitle\n---\n# One\n- a\n---\n# Two\n- b\n---\n# Three\n- c\n"
        "---\n# Four\n- d\n---\n# Closing\nThanks\n"
    )
    tools["fill_pptx_template"](
        path="grow.pptx", template_id="bold-statement", content=grow_content
    )
    prs_grow = Presentation(str(tmp_path / "grow.pptx"))
    assert len(prs_grow.slides) == 6

    shrink_content = "# Title\nSubtitle\n---\n# Only\n- a\n---\n# Closing\nThanks\n"
    tools["fill_pptx_template"](
        path="shrink.pptx", template_id="bold-statement", content=shrink_content
    )
    prs_shrink = Presentation(str(tmp_path / "shrink.pptx"))
    assert len(prs_shrink.slides) == 3


def _tools_with_custom_templates_dir(root: Path, templates_dir: Path) -> dict[str, object]:
    return {
        tool.__name__: tool
        for tool in build_presentation_tools(root, custom_templates_dir=templates_dir)  # type: ignore[attr-defined]
    }


def test_extract_pptx_template_classifies_roles_matching_the_real_manifest(
    tmp_path: Path,
) -> None:
    """Extracts from one of coscribe's own bundled templates (used here
    purely as a stand-in "reference deck") -- its own real template.yaml
    is independently-known ground truth to check the role-classification
    heuristic (first=title, last=closing, middle=content) against."""

    workspace = tmp_path / "workspace"
    workspace.mkdir()
    templates_dir = tmp_path / "custom_templates"
    bundled = (
        Path(__file__).parents[4]
        / "src/coscribe/builtin_templates/pptx/bold-statement/template.pptx"
    )
    shutil.copy(bundled, workspace / "reference.pptx")
    tools = _tools_with_custom_templates_dir(workspace, templates_dir)

    result = tools["extract_pptx_template"](
        source_path="reference.pptx",
        template_id="test-extracted",
        name="Test Extracted",
        description="A distilled copy of bold-statement, for testing",
    )

    import re

    assert result["slide_roles"] == ["title", "content", "content", "closing"]
    assert result["slide_count"] == 4
    assert re.match(r"^[0-9A-Fa-f]{6}$", result["accent"])
    assert (templates_dir / "test-extracted" / "template.pptx").is_file()
    assert (templates_dir / "test-extracted" / "template.yaml").is_file()


def test_extract_pptx_template_is_immediately_usable_by_fill_pptx_template(
    tmp_path: Path,
) -> None:

    from pptx import Presentation

    workspace = tmp_path / "workspace"
    workspace.mkdir()
    templates_dir = tmp_path / "custom_templates"
    bundled = (
        Path(__file__).parents[4]
        / "src/coscribe/builtin_templates/pptx/bold-statement/template.pptx"
    )
    shutil.copy(bundled, workspace / "reference.pptx")
    tools = _tools_with_custom_templates_dir(workspace, templates_dir)
    tools["extract_pptx_template"](
        source_path="reference.pptx",
        template_id="my-brand",
        name="My Brand",
        description="test",
    )

    result = tools["fill_pptx_template"](
        path="out.pptx",
        template_id="my-brand",
        content="# Real Title\n- point one\n---\n# Closing\nThanks",
    )

    assert result["template_id"] == "my-brand"
    prs = Presentation(str(workspace / "out.pptx"))
    assert prs.slides[0].shapes.title.text == "Real Title"


def test_extract_pptx_template_rejects_slide_with_no_usable_placeholder(
    tmp_path: Path,
) -> None:
    from pptx import Presentation
    from pptx.util import Inches

    workspace = tmp_path / "workspace"
    workspace.mkdir()
    templates_dir = tmp_path / "custom_templates"

    prs = Presentation()
    s1 = prs.slides.add_slide(prs.slide_layouts[0])
    s1.shapes.title.text = "A Title"
    s2 = prs.slides.add_slide(prs.slide_layouts[6])  # blank -- no placeholders at all
    s2.shapes.add_textbox(Inches(1), Inches(1), Inches(2), Inches(1)).text_frame.text = "plain text"
    prs.save(str(workspace / "messy.pptx"))
    tools = _tools_with_custom_templates_dir(workspace, templates_dir)

    with pytest.raises(ValueError, match="Slide 2 of 'messy.pptx' has no usable"):
        tools["extract_pptx_template"](
            source_path="messy.pptx", template_id="messy", name="Messy", description="test"
        )


def test_extract_pptx_template_rejects_duplicate_id_without_overwrite(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    templates_dir = tmp_path / "custom_templates"
    tools = _tools_with_custom_templates_dir(workspace, templates_dir)
    tools["write_pptx"](path="ref.pptx", content="# Title\n- bullet")
    tools["extract_pptx_template"](
        source_path="ref.pptx", template_id="dup", name="Dup", description="test"
    )

    with pytest.raises(FileExistsError, match="already exists"):
        tools["extract_pptx_template"](
            source_path="ref.pptx", template_id="dup", name="Dup Again", description="test"
        )

    # overwrite=True is the escape hatch
    tools["extract_pptx_template"](
        source_path="ref.pptx",
        template_id="dup",
        name="Dup Replaced",
        description="test",
        overwrite=True,
    )


def test_extract_pptx_template_rejects_bad_template_id(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    templates_dir = tmp_path / "custom_templates"
    tools = _tools_with_custom_templates_dir(workspace, templates_dir)
    tools["write_pptx"](path="ref.pptx", content="# Title\n- bullet")

    with pytest.raises(ValueError, match="lowercase letters/digits/hyphens"):
        tools["extract_pptx_template"](
            source_path="ref.pptx", template_id="Not Valid!", name="X", description="test"
        )


def test_extract_pptx_template_requires_custom_templates_dir_configured(tmp_path: Path) -> None:
    tools = _tools_by_name(tmp_path)  # no custom_templates_dir passed
    tools["write_pptx"](path="ref.pptx", content="# Title\n- bullet")

    with pytest.raises(ValueError, match="No custom templates directory"):
        tools["extract_pptx_template"](
            source_path="ref.pptx", template_id="x", name="X", description="test"
        )


def test_extract_pptx_template_is_write_local_and_gated(tmp_path: Path) -> None:
    from coscribe.runtime import get_tool_metadata

    workspace = tmp_path / "workspace"
    workspace.mkdir()
    tools = _tools_with_custom_templates_dir(workspace, tmp_path / "custom_templates")
    metadata = get_tool_metadata(tools["extract_pptx_template"])
    assert metadata.risk_category == "WRITE_LOCAL"
    assert metadata.requires_approval is True


def test_fill_pptx_template_chunk_with_heading_but_no_title_placeholder_raises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _make_fake_template(tmp_path, monkeypatch, [6])  # "Blank" -- no placeholders at all
    tools = _tools_by_name(tmp_path / "workspace")

    with pytest.raises(ValueError, match="no title placeholder"):
        tools["fill_pptx_template"](path="out.pptx", template_id="fake", content="# A Title")


def test_fill_pptx_template_chunk_with_body_but_no_body_placeholder_raises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _make_fake_template(tmp_path, monkeypatch, [5])  # "Title Only" -- no body placeholder
    tools = _tools_by_name(tmp_path / "workspace")

    with pytest.raises(ValueError, match="no body"):
        tools["fill_pptx_template"](
            path="out.pptx", template_id="fake", content="# Title\n- a bullet"
        )


def test_fill_pptx_template_replaces_existing_placeholder_text_instead_of_appending(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Regression test for a real, live-found bug: coscribe's own bundled
    templates are authored with empty placeholders, so _set_title/
    _fill_content_placeholder appending straight into paragraphs[0] was
    invisible. Any real-world template (confirmed live against an actual
    Microsoft-authored one, "The science of public speaking") ships with
    real sample text already in its placeholders -- appending onto that
    produced garbled runs like "Know your material in advanceNEW BULLET
    A", and any of the template's *own* extra paragraphs past the first
    survived untouched. This pre-fills a fake template's title and body
    placeholder with sample text/multiple paragraphs the way a real
    template would, then asserts fill_pptx_template's output has *only*
    the new content, cleanly."""
    from pptx import Presentation

    _make_fake_template(tmp_path, monkeypatch, [1])
    template_path = tmp_path / "fake_template.pptx"
    prs = Presentation(str(template_path))
    slide = prs.slides[0]
    slide.shapes.title.text_frame.text = "Old Sample Title"
    body = next(
        p
        for p in slide.placeholders
        if p.placeholder_format.idx != slide.shapes.title.placeholder_format.idx
    )
    body.text_frame.text = "Old sample line one"
    body.text_frame.add_paragraph().text = "Old sample line two"
    prs.save(str(template_path))

    tools = _tools_by_name(tmp_path / "workspace")
    tools["fill_pptx_template"](
        path="out.pptx", template_id="fake", content="# New Title\n- new bullet"
    )

    result_prs = Presentation(str(tmp_path / "workspace" / "out.pptx"))
    result_slide = result_prs.slides[0]
    assert result_slide.shapes.title.text == "New Title"
    result_body = next(
        p
        for p in result_slide.placeholders
        if p.placeholder_format.idx != result_slide.shapes.title.placeholder_format.idx
    )
    assert [p.text for p in result_body.text_frame.paragraphs] == ["new bullet"]


def test_find_body_placeholder_skips_a_table_occupying_the_content_placeholder(
    tmp_path: Path,
) -> None:
    """Regression test for a real, live-found crash: a real-world
    template's content placeholder slot can already hold a native table
    (a GraphicFrame, not a text-frame shape) rather than plain text --
    confirmed live against a real Microsoft-authored template's "Agenda"
    slide. Before this fix, _find_body_placeholder still matched it (its
    placeholder_format.type is OBJECT, same as a text one), and
    fill_pptx_template's caller then crashed with an opaque
    AttributeError: 'PlaceholderGraphicFrame' object has no attribute
    'text_frame' trying to write into it -- rather than the same clean,
    actionable "no body/content placeholder" ValueError a slide with no
    eligible placeholder at all already produces. Exercises
    _find_body_placeholder directly against lightweight stand-ins (no real
    OOXML table-in-placeholder XML needed -- python-pptx's own creation
    API in this version can't build one, only read one) rather than
    fill_pptx_template's full public path, which the happy-path/no-body
    tests above already cover end to end."""
    from pptx.enum.shapes import PP_PLACEHOLDER

    from coscribe.tools.office.pptx.slide_builders import find_body_placeholder

    class _FakePlaceholderFormat:
        def __init__(self, type_: object, idx: int) -> None:
            self.type = type_
            self.idx = idx

    class _FakeShape:
        def __init__(self, type_: object, idx: int, shape_id: int, has_text_frame: bool) -> None:
            self.placeholder_format = _FakePlaceholderFormat(type_, idx)
            self.shape_id = shape_id
            self.has_text_frame = has_text_frame

    class _FakeShapes:
        def __init__(self, title: object) -> None:
            self.title = title

    class _FakeSlide:
        def __init__(self, title: object, placeholders: list[object]) -> None:
            self.shapes = _FakeShapes(title)
            self.placeholders = placeholders

    title_shape = _FakeShape(PP_PLACEHOLDER.TITLE, idx=0, shape_id=1, has_text_frame=True)
    table_shape = _FakeShape(PP_PLACEHOLDER.OBJECT, idx=1, shape_id=2, has_text_frame=False)
    slide = _FakeSlide(title_shape, [title_shape, table_shape])

    assert find_body_placeholder(slide) is None


def test_fill_pptx_template_rejects_layout_directive_naming_write_pptx(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _make_fake_template(tmp_path, monkeypatch, [1])
    tools = _tools_by_name(tmp_path / "workspace")

    with pytest.raises(ValueError, match="write_pptx"):
        tools["fill_pptx_template"](
            path="out.pptx",
            template_id="fake",
            content="layout: icon-list\n# Title\n- x",
        )


def test_fill_pptx_template_rejects_table_naming_write_pptx(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _make_fake_template(tmp_path, monkeypatch, [1])
    tools = _tools_by_name(tmp_path / "workspace")

    with pytest.raises(ValueError, match="write_pptx"):
        tools["fill_pptx_template"](
            path="out.pptx",
            template_id="fake",
            content="# Title\n| a | b |\n| --- | --- |\n| 1 | 2 |",
        )


def test_fill_pptx_template_unknown_template_id_raises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _make_fake_template(tmp_path, monkeypatch, [1], template_id="fake")
    tools = _tools_by_name(tmp_path / "workspace")

    with pytest.raises(ValueError, match="Unknown template"):
        tools["fill_pptx_template"](path="out.pptx", template_id="nope", content="# Title")


def test_fill_pptx_template_is_medium_risk_and_requires_approval(tmp_path: Path) -> None:
    from coscribe.runtime import get_tool_metadata

    tools = _tools_by_name(tmp_path)
    metadata = get_tool_metadata(tools["fill_pptx_template"])
    assert metadata.risk_category == "WRITE_LOCAL"
    assert metadata.requires_approval is True


def test_fill_pptx_template_respects_overwrite_false(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _make_fake_template(tmp_path, monkeypatch, [1])
    tools = _tools_by_name(tmp_path / "workspace")
    tools["fill_pptx_template"](path="out.pptx", template_id="fake", content="# Title\n- x")

    with pytest.raises(FileExistsError):
        tools["fill_pptx_template"](
            path="out.pptx", template_id="fake", content="# Title\n- x", overwrite=False
        )
