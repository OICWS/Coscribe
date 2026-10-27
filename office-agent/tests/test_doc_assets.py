"""Pictures of a Doc (decision 0025): kept in the side folder, read by their markdown path only."""

from __future__ import annotations

import io
from pathlib import Path

import pytest
from PIL import Image

from coscribe.tools.office.doc import DocAssetRefused, add_doc_asset, read_doc_asset


def _png(size: tuple[int, int] = (4, 3)) -> bytes:
    out = io.BytesIO()
    Image.new("RGB", size, "red").save(out, "PNG")
    return out.getvalue()


def _doc(tmp_path: Path) -> Path:
    path = tmp_path / "plan.md"
    path.write_text("---\ncoscribe: doc\n---\n\nText.\n", encoding="utf-8")
    return path


def test_a_picture_is_kept_beside_the_doc_and_read_back_by_its_markdown_path(
    tmp_path: Path,
) -> None:
    path = _doc(tmp_path)

    added = add_doc_asset(path, "My chart!.png", _png())
    again = add_doc_asset(path, "My chart!.png", _png())
    read = read_doc_asset(path, added["src"])

    assert added["src"] == "plan.doc/assets/My-chart.png"
    assert (added["width"], added["height"]) == (4, 3)
    assert again["src"] == "plan.doc/assets/My-chart-2.png"
    assert read is not None and read[1] == "image/png" and read[0] == _png()


def test_what_is_not_a_picture_of_this_doc_is_refused_or_not_found(tmp_path: Path) -> None:
    path = _doc(tmp_path)
    (tmp_path / "secret.png").write_bytes(_png())
    (tmp_path / "plan.doc" / "assets").mkdir(parents=True)
    (tmp_path / "plan.doc" / "assets" / "note.txt").write_text("x", encoding="utf-8")
    svg = b"<svg xmlns='http://www.w3.org/2000/svg'/>"

    with pytest.raises(DocAssetRefused) as text:
        add_doc_asset(path, "a.png", b"not a picture")
    with pytest.raises(DocAssetRefused) as big:
        add_doc_asset(path, "a.png", b"0" * (8 * 1024 * 1024 + 1))
    with pytest.raises(DocAssetRefused) as vector:
        add_doc_asset(path, "a.svg", svg)

    assert [text.value.code, big.value.code, vector.value.code] == [
        "not_a_picture",
        "too_big",
        "not_a_picture",
    ]
    for src in (
        "../secret.png",
        "plan.doc/assets/../../secret.png",
        "other.doc/assets/x.png",
        "plan.doc/assets/note.txt",
        "plan.doc/assets/missing.png",
        "plan.doc/versions/index.json",
        "",
    ):
        assert read_doc_asset(path, src) is None
