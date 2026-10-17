import zipfile
from pathlib import Path

import pytest

from tests.libreoffice_probe import convert_with_libreoffice

from .helpers import (
    _A_NS,
    _P14_NS,
    _P_NS,
    _libreoffice_actually_works,
    _tools_by_name,
    _write_wav,
)


def test_add_pptx_audio_embeds_a_real_media_part_and_relationships(tmp_path: Path) -> None:
    from pptx import Presentation
    from pptx.opc.constants import RELATIONSHIP_TYPE as RT

    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- body")
    _write_wav(tmp_path / "narration.wav")

    tools["add_pptx_audio"](path="deck.pptx", slide=1, audio_path="narration.wav")

    prs = Presentation(tmp_path / "deck.pptx")
    slide_part = prs.slides[0].part
    rel_types = {rel.reltype for rel in slide_part.rels.values()}
    assert RT.AUDIO in rel_types
    assert RT.MEDIA in rel_types
    assert RT.IMAGE in rel_types  # the poster icon

    pic = prs.slides[0].element.find(f".//{{{_P_NS}}}pic")
    assert pic is not None
    assert pic.find(f".//{{{_A_NS}}}audioFile") is not None
    assert pic.find(f".//{{{_P_NS}}}extLst/{{{_P_NS}}}ext/{{{_P14_NS}}}media") is not None
    assert pic.find(f".//{{{_A_NS}}}blip") is not None


def test_add_pptx_audio_declares_the_p14_prefix(tmp_path: Path) -> None:
    """Without a declared prefix lxml names p14 `ns<N>`, with N depending on what the process did
    before, so the same call wrote different bytes in different runs."""

    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- body")
    _write_wav(tmp_path / "narration.wav")

    tools["add_pptx_audio"](path="deck.pptx", slide=1, audio_path="narration.wav")

    from lxml import etree

    with zipfile.ZipFile(tmp_path / "deck.pptx") as archive:
        slide = etree.fromstring(archive.read("ppt/slides/slide1.xml"))
    (media,) = slide.iter(f"{{{_P14_NS}}}media")
    assert media.prefix == "p14"
    assert not [element for element in slide.iter() if (element.prefix or "").startswith("ns")]


def test_add_pptx_audio_auto_trigger_builds_delayed_timing_node(tmp_path: Path) -> None:
    from pptx import Presentation

    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- body")
    _write_wav(tmp_path / "narration.wav")

    tools["add_pptx_audio"](path="deck.pptx", slide=1, audio_path="narration.wav", start_delay=2.5)

    prs = Presentation(tmp_path / "deck.pptx")
    timing = prs.slides[0].element.find(f"{{{_P_NS}}}timing")
    assert timing is not None
    audio_node = timing.find(f".//{{{_P_NS}}}audio")
    assert audio_node is not None
    cond = audio_node.find(f".//{{{_P_NS}}}cTn/{{{_P_NS}}}stCondLst/{{{_P_NS}}}cond")
    assert cond.get("delay") == "2500"


def test_add_pptx_audio_on_click_trigger_uses_indefinite_delay(tmp_path: Path) -> None:
    from pptx import Presentation

    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- body")
    _write_wav(tmp_path / "narration.wav")

    tools["add_pptx_audio"](
        path="deck.pptx", slide=1, audio_path="narration.wav", trigger="on-click"
    )

    prs = Presentation(tmp_path / "deck.pptx")
    timing = prs.slides[0].element.find(f"{{{_P_NS}}}timing")
    cond = timing.find(f".//{{{_P_NS}}}audio//{{{_P_NS}}}cond")
    assert cond.get("delay") == "indefinite"


def test_add_pptx_audio_hidden_moves_shape_off_canvas(tmp_path: Path) -> None:
    from pptx import Presentation

    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- body")
    _write_wav(tmp_path / "narration.wav")

    tools["add_pptx_audio"](path="deck.pptx", slide=1, audio_path="narration.wav", hidden=True)

    prs = Presentation(tmp_path / "deck.pptx")
    pic = prs.slides[0].element.find(f".//{{{_P_NS}}}pic")
    off = pic.find(f".//{{{_A_NS}}}xfrm/{{{_A_NS}}}off")
    assert int(off.get("x")) < 0
    assert int(off.get("y")) < 0


def test_add_pptx_audio_visible_places_shape_at_requested_position(tmp_path: Path) -> None:
    from pptx import Presentation
    from pptx.util import Inches

    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- body")
    _write_wav(tmp_path / "narration.wav")

    tools["add_pptx_audio"](
        path="deck.pptx", slide=1, audio_path="narration.wav", left_in=1.5, top_in=2.0
    )

    prs = Presentation(tmp_path / "deck.pptx")
    pic = prs.slides[0].element.find(f".//{{{_P_NS}}}pic")
    off = pic.find(f".//{{{_A_NS}}}xfrm/{{{_A_NS}}}off")
    assert int(off.get("x")) == int(Inches(1.5))
    assert int(off.get("y")) == int(Inches(2.0))


def test_add_pptx_audio_rejects_unknown_trigger(tmp_path: Path) -> None:
    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- body")
    _write_wav(tmp_path / "narration.wav")

    with pytest.raises(ValueError, match="Unknown trigger"):
        tools["add_pptx_audio"](
            path="deck.pptx", slide=1, audio_path="narration.wav", trigger="bogus"
        )


@pytest.mark.parametrize("extension", [".mp3", ".m4a", ".wav"])
def test_add_pptx_audio_accepts_every_supported_extension(tmp_path: Path, extension: str) -> None:
    """WAV is the only format the other tests exercise with real,
    decodable audio bytes (no ffmpeg available in this environment to
    generate real mp3/m4a) -- nothing in the embed path actually decodes
    the audio (matching real PowerPoint's own extension-trusting insert
    behavior), so plausible-but-fake bytes are enough to confirm the
    extension -> content-type mapping doesn't have a format-specific bug
    for mp3/m4a specifically, not just wav."""
    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- body")
    audio_path = tmp_path / f"clip{extension}"
    if extension == ".wav":
        _write_wav(audio_path)
    else:
        audio_path.write_bytes(b"\x00" * 256)

    result = tools["add_pptx_audio"](path="deck.pptx", slide=1, audio_path=f"clip{extension}")

    assert result["shape_index"] == 2


def test_add_pptx_audio_rejects_unsupported_format(tmp_path: Path) -> None:
    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- body")
    (tmp_path / "song.ogg").write_bytes(b"not actually audio")

    with pytest.raises(ValueError, match="unsupported audio format"):
        tools["add_pptx_audio"](path="deck.pptx", slide=1, audio_path="song.ogg")


def test_add_pptx_audio_rejects_missing_file(tmp_path: Path) -> None:
    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- body")

    with pytest.raises(ValueError, match="does not exist"):
        tools["add_pptx_audio"](path="deck.pptx", slide=1, audio_path="missing.mp3")


def test_add_pptx_audio_two_calls_share_one_media_part(tmp_path: Path) -> None:
    """Regression test for a real bug: python-pptx's own `PartFactory`
    ships with no content-type registered for any media part, so
    reopening a .pptx that already has one audio part loads it back as a
    plain `Part` (no `.sha1`), and `get_or_add_media_part`'s own
    dedup-by-sha1 lookup used to crash with `AttributeError: 'Part'
    object has no attribute 'sha1'` on a second add_pptx_audio call in
    the same process -- hit for real before
    `_register_audio_media_part_class` fixed it, not a hypothetical."""
    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# S1\n- a\n---\n# S2\n- b")
    _write_wav(tmp_path / "narration.wav")

    tools["add_pptx_audio"](path="deck.pptx", slide=1, audio_path="narration.wav")
    tools["add_pptx_audio"](path="deck.pptx", slide=2, audio_path="narration.wav")

    from pptx import Presentation

    audio_tag = "{http://schemas.openxmlformats.org/drawingml/2006/main}audioFile"
    link_attr = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}link"
    prs = Presentation(tmp_path / "deck.pptx")
    targets = set()
    for slide in prs.slides:
        audio = slide.element.find(f".//{audio_tag}")
        assert audio is not None
        targets.add(slide.part.related_part(audio.get(link_attr)).partname)
    # One shared part, not a copy per call.
    assert len(targets) == 1
    with zipfile.ZipFile(tmp_path / "deck.pptx") as archive:
        media = [n for n in archive.namelist() if n.startswith("ppt/media/") and n.endswith(".wav")]
    assert len(media) == 1


def test_add_pptx_audio_after_animation_shares_the_existing_timing_tree(
    tmp_path: Path,
) -> None:
    from pptx import Presentation

    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- body")
    _write_wav(tmp_path / "narration.wav")

    tools["add_pptx_animation"](path="deck.pptx", slide=1, shape_index=0, animation="fade")
    tools["add_pptx_audio"](path="deck.pptx", slide=1, audio_path="narration.wav")

    prs = Presentation(tmp_path / "deck.pptx")
    timing_elements = prs.slides[0].element.findall(f"{{{_P_NS}}}timing")
    assert len(timing_elements) == 1
    root_child = timing_elements[0].find(
        f".//{{{_P_NS}}}cTn[@nodeType='tmRoot']/{{{_P_NS}}}childTnLst"
    )
    child_tags = {child.tag.rsplit("}", 1)[-1] for child in root_child}
    assert child_tags == {"seq", "audio"}


def test_add_pptx_animation_after_audio_adds_a_mainseq_without_losing_the_audio(
    tmp_path: Path,
) -> None:
    """Regression test for a real bug: add_pptx_audio (called first)
    creates a minimal <p:timing> tree with no mainSeq at all (an empty
    <p:seq> would itself be schema-invalid) -- add_pptx_animation must
    add a mainSeq to that SAME tree rather than assuming a missing
    mainSeq means a missing <p:timing> entirely and recreating (which
    would silently discard the audio node already there)."""
    from pptx import Presentation

    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# Title\n- body")
    _write_wav(tmp_path / "narration.wav")

    tools["add_pptx_audio"](path="deck.pptx", slide=1, audio_path="narration.wav")
    tools["add_pptx_animation"](path="deck.pptx", slide=1, shape_index=0, animation="fade")

    prs = Presentation(tmp_path / "deck.pptx")
    timing_elements = prs.slides[0].element.findall(f"{{{_P_NS}}}timing")
    assert len(timing_elements) == 1
    root_child = timing_elements[0].find(
        f".//{{{_P_NS}}}cTn[@nodeType='tmRoot']/{{{_P_NS}}}childTnLst"
    )
    child_tags = {child.tag.rsplit("}", 1)[-1] for child in root_child}
    assert child_tags == {"seq", "audio"}
    # The audio node itself must still be present and intact, not
    # silently dropped by a from-scratch timing-tree rebuild.
    audio_node = timing_elements[0].find(f".//{{{_P_NS}}}audio")
    assert audio_node is not None


def test_add_pptx_audio_is_medium_risk_and_requires_approval(tmp_path: Path) -> None:
    from coscribe.runtime import get_tool_metadata

    tools = _tools_by_name(tmp_path)
    metadata = get_tool_metadata(tools["add_pptx_audio"])
    assert metadata.risk_category == "WRITE_LOCAL"
    assert metadata.requires_approval is True


@pytest.mark.real_libreoffice
@pytest.mark.skipif(
    not _libreoffice_actually_works(),
    reason="LibreOffice not installed or not functional in this environment",
)
def test_add_pptx_audio_survives_libreoffice_conversion_in_both_orders(
    tmp_path: Path,
) -> None:
    """Auto/on-click/hidden variants, plus both add_pptx_audio/
    add_pptx_animation call orders, on one real 2-slide deck -- can't
    verify playback itself in a static test (that needs a human with
    real PowerPoint/LibreOffice), but a real subprocess conversion
    succeeding, plus a warnings-as-errors python-pptx round-trip, is the
    strongest automated check available."""
    import warnings

    from pptx import Presentation

    tools = _tools_by_name(tmp_path)
    tools["write_pptx"](path="deck.pptx", content="# S1\n- a\n- b\n---\n# S2\n- c\n- d")
    _write_wav(tmp_path / "narration.wav")

    tools["add_pptx_animation"](path="deck.pptx", slide=1, shape_index=0, animation="fade")
    tools["add_pptx_audio"](path="deck.pptx", slide=1, audio_path="narration.wav", start_delay=0.5)
    tools["add_pptx_audio"](
        path="deck.pptx", slide=2, audio_path="narration.wav", trigger="on-click", hidden=True
    )
    tools["add_pptx_animation"](path="deck.pptx", slide=2, shape_index=0, animation="fly-in")

    with warnings.catch_warnings():
        warnings.simplefilter("error")
        prs = Presentation(tmp_path / "deck.pptx")
        assert len(prs.slides) == 2

    convert_with_libreoffice(tmp_path / "deck.pptx", tmp_path)
    assert (tmp_path / "deck.pdf").is_file()
