"""The text widths the deck engine sizes boxes with: Latin text in the face PowerPoint draws it in,
and the Windows table, equal to the fonts it was measured on (on the Windows job), for the CJK
faces upstream has no advances for."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

from coscribe.tools._native_svg.svg_to_pptx.drawingml import utils

_ROOT = Path(__file__).resolve().parents[1]
_TABLE = _ROOT / "src/coscribe/tools/_native_svg/svg_to_pptx/drawingml/font_advances_windows.json"
_FONTS = Path("C:/Windows/Fonts")


def _script() -> object:
    spec = importlib.util.spec_from_file_location(
        "measure_font_advances", _ROOT / "scripts/measure_font_advances.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.skipif(
    sys.platform != "win32" or not _FONTS.exists(), reason="measures the Windows fonts"
)
def test_the_table_equals_the_fonts_on_this_machine() -> None:
    script = _script()
    committed = json.loads(_TABLE.read_text(encoding="utf-8"))["families"]

    measured, _missing = script.measure(_FONTS, script.FONTS)  # type: ignore[attr-defined]

    assert script._differences(committed, measured) == []  # type: ignore[attr-defined]


def test_a_family_in_the_table_sizes_its_latin_text() -> None:
    families = json.loads(_TABLE.read_text(encoding="utf-8"))["families"]
    advances = families["microsoft yahei"]["regular"]["advances"]

    width = sum(
        utils.estimate_text_cluster_widths("Q3 2026", 40, font_family="Microsoft YaHei, sans-serif")
    )

    assert width == pytest.approx(sum(advances[ch] for ch in "Q3 2026") * 40)


def test_latin_text_is_sized_in_the_face_powerpoint_draws_it_in() -> None:
    # The emitter writes `a:latin` as Arial for this stack, so its digits are Arial's.
    arial = utils.get_font_advances("Arial")
    assert arial is not None

    width = sum(
        utils.estimate_text_cluster_widths("5,410", 36, font_family="Microsoft YaHei, Arial")
    )

    assert width == pytest.approx(sum(arial[ch] for ch in "5,410") * 36)
