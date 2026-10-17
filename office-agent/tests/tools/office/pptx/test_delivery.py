import shutil
import zipfile
from pathlib import Path

from .helpers import (
    _tools_by_name,
    _write_wav,
)


def test_check_pptx_delivery_clean_deck_has_no_advisories(tmp_path: Path) -> None:
    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- body")

    report = tools["check_pptx_delivery"](path="deck.pptx")

    assert report["path"] == "deck.pptx"
    assert report["zip_integrity"] == "ok"
    assert report["corrupt_member"] is None
    assert report["duplicate_parts"] == []
    assert report["slide_count"] == 1
    assert report["hidden_slides"] == []
    assert report["fonts"]["unsafe"] == []
    assert report["advisories"] == []


def test_check_pptx_delivery_reports_motion_summary_per_category(tmp_path: Path) -> None:
    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# S1\n- a\n---\n# S2\n- b\n---\n# S3\n- c")
    tools["set_pptx_transition"](path="deck.pptx", slide=1, transition="fade")
    tools["add_pptx_animation"](path="deck.pptx", slide=2, shape_index=0, animation="fade")
    _write_wav(tmp_path / "narration.wav")
    tools["add_pptx_audio"](path="deck.pptx", slide=3, audio_path="narration.wav")

    report = tools["check_pptx_delivery"](path="deck.pptx")

    assert report["motion"] == {
        "transitions": [1],
        "animations": [2],
        "audio": [3],
    }


def test_check_pptx_delivery_flags_hidden_slide(tmp_path: Path) -> None:
    from pptx import Presentation

    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# S1\n- a\n---\n# S2\n- b")

    prs = Presentation(tmp_path / "deck.pptx")
    prs.slides[0].element.set("show", "0")
    prs.save(str(tmp_path / "deck.pptx"))

    report = tools["check_pptx_delivery"](path="deck.pptx")

    assert report["hidden_slides"] == [1]
    assert any("hidden slide" in advisory for advisory in report["advisories"])


def test_check_pptx_delivery_flags_unsafe_font(tmp_path: Path) -> None:
    from pptx import Presentation

    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- body")

    prs = Presentation(tmp_path / "deck.pptx")
    box = prs.slides[0].shapes.add_textbox(0, 0, 100, 100)
    run = box.text_frame.paragraphs[0].add_run()
    run.text = "test"
    run.font.name = "Comic Sans MS"
    prs.save(str(tmp_path / "deck.pptx"))

    report = tools["check_pptx_delivery"](path="deck.pptx")

    assert report["fonts"]["unsafe"] == ["Comic Sans MS"]
    assert "Calibri" in report["fonts"]["used"]  # the safe default title/body font
    assert any("cross-platform-safe" in advisory for advisory in report["advisories"])


def test_check_pptx_delivery_flags_oversized_media(tmp_path: Path) -> None:
    from coscribe.tools.office.pptx import toolkit_helpers as presentations_module

    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- body")

    original_threshold = presentations_module.DELIVERY_MEDIA_ADVISORY_BYTES
    # -1, not a small positive number: a plain write_pptx deck may have
    # zero embedded media (no images at all), so the threshold must be
    # guaranteed below the real total (0 bytes included) to reliably
    # trigger the advisory regardless of what write_pptx happens to
    # embed.
    presentations_module.DELIVERY_MEDIA_ADVISORY_BYTES = -1
    try:
        report = tools["check_pptx_delivery"](path="deck.pptx")
    finally:
        presentations_module.DELIVERY_MEDIA_ADVISORY_BYTES = original_threshold

    assert any("Embedded media totals" in advisory for advisory in report["advisories"])


def test_check_pptx_delivery_reports_duplicate_package_parts(tmp_path: Path) -> None:

    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- body")
    shutil.copy(tmp_path / "deck.pptx", tmp_path / "dup.pptx")
    with zipfile.ZipFile(tmp_path / "dup.pptx", "a") as archive:
        archive.writestr("ppt/slides/slide1.xml", b"<p:sld/>")

    report = tools["check_pptx_delivery"](path="dup.pptx")

    assert report["duplicate_parts"] == ["ppt/slides/slide1.xml"]
    assert any("Duplicate package parts" in advisory for advisory in report["advisories"])


def test_check_pptx_delivery_falls_back_gracefully_when_python_pptx_cannot_parse(
    tmp_path: Path,
) -> None:
    """Regression test for a real bug: without a broad fallback around
    the python-pptx-dependent half of the audit, a file broken enough
    that python-pptx itself chokes on it (here: a duplicate slide1.xml
    entry that resolves to garbage content) crashed the whole tool
    instead of returning the raw package-level findings the zip-level
    pass already had -- confirmed by hitting the real
    AttributeError before adding the fallback, not assumed necessary."""

    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- body")
    shutil.copy(tmp_path / "deck.pptx", tmp_path / "broken.pptx")
    with zipfile.ZipFile(tmp_path / "broken.pptx", "a") as archive:
        archive.writestr("ppt/slides/slide1.xml", b"<p:sld/>")

    report = tools["check_pptx_delivery"](path="broken.pptx")

    assert report["duplicate_parts"] == ["ppt/slides/slide1.xml"]
    assert report["slide_count"] is None
    assert report["hidden_slides"] is None
    assert report["fonts"] is None
    assert report["motion"] is None
    assert any("Could not fully analyze" in advisory for advisory in report["advisories"])
    # media info still came from the raw-zip pass, unaffected by the
    # python-pptx-side failure.
    assert report["media"]["count"] >= 0


def test_check_pptx_delivery_is_read_and_no_approval(tmp_path: Path) -> None:
    from coscribe.runtime import get_tool_metadata

    tools = _tools_by_name(tmp_path)
    metadata = get_tool_metadata(tools["check_pptx_delivery"])
    assert metadata.risk_category == "READ"
    assert metadata.requires_approval is False
