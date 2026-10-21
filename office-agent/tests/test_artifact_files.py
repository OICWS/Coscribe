"""What the Artifacts menu does to a file: a name is checked, a copy never overwrites, and a
deck's pages folder follows the deck, so the copy and the renamed deck still open in the panel."""

from __future__ import annotations

from pathlib import Path

import pytest

from coscribe.conversation.artifact_files import (
    ArtifactFileError,
    copy_file,
    free_copy_path,
    rename_file,
    renamed_path,
    trash_file,
)
from coscribe.tools.office.pptx import deck_files, read_deck
from coscribe.tools.office.pptx.engine import build_deck

from .test_deck_engine import CARDS, COVER


def _deck(tmp_path: Path) -> Path:
    folder = tmp_path / "pages"
    folder.mkdir()
    (folder / "01-cover.svg").write_text(COVER, encoding="utf-8")
    (folder / "02-cards.svg").write_text(CARDS, encoding="utf-8")
    assert build_deck(folder, tmp_path / "deck.pptx", resource_root=tmp_path).ok
    return tmp_path / "deck.pptx"


@pytest.mark.parametrize("name", ["", "  ", "a/b", "a:b", ".hidden", "ends.", "what?"])
def test_a_name_that_cannot_be_a_file_is_refused(tmp_path: Path, name: str) -> None:
    file = tmp_path / "report.docx"
    file.write_bytes(b"x")
    with pytest.raises(ArtifactFileError):
        renamed_path(file, name)


def test_a_rename_keeps_the_ending_and_never_overwrites(tmp_path: Path) -> None:
    file = tmp_path / "report.docx"
    file.write_bytes(b"x")
    (tmp_path / "taken.docx").write_bytes(b"y")
    assert renamed_path(file, "Plan").name == "Plan.docx"
    assert renamed_path(file, "Plan.docx").name == "Plan.docx"
    with pytest.raises(ArtifactFileError):
        renamed_path(file, "taken")
    assert rename_file(file, "Plan") == tmp_path / "Plan.docx"
    assert not file.exists()


def test_a_copy_takes_the_first_free_name(tmp_path: Path) -> None:
    file = tmp_path / "report.docx"
    file.write_bytes(b"x")
    assert copy_file(file).name == "report copy.docx"
    assert free_copy_path(file).name == "report copy 2.docx"
    assert (tmp_path / "report copy.docx").read_bytes() == b"x"


def test_a_renamed_deck_still_opens_with_its_pages(tmp_path: Path) -> None:
    deck = _deck(tmp_path)
    target = rename_file(deck, "Quarter")
    slides = read_deck(target)["slides"]
    assert [s["name"] for s in slides] == ["01-cover.svg", "02-cards.svg"]
    assert not read_deck(target)["changed"]


def test_a_copied_deck_has_its_own_pages(tmp_path: Path) -> None:
    deck = _deck(tmp_path)
    twin = copy_file(deck)
    assert twin.name == "deck copy.pptx"
    assert [s["name"] for s in read_deck(twin)["slides"]] == ["01-cover.svg", "02-cards.svg"]
    folders = {f for f in (deck_files(deck)[1], deck_files(twin)[1])}
    assert len(folders) == 2  # not the same folder: editing one leaves the other


def test_delete_sends_the_deck_and_its_pages_to_the_recycle_bin(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    deck = _deck(tmp_path)
    sent: list[str] = []
    monkeypatch.setattr("send2trash.send2trash", sent.append)
    trash_file(deck)
    assert sent == [str(deck), str(tmp_path / "pages")]
