"""The versions of a document the Docs editor has held (decision 0019): what is kept, what one step
is, and what an undo may and may not do."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from coscribe.tools.office.document_tools import build_document_tools
from coscribe.tools.office.docx import (
    DocChanged,
    VersionGone,
    history,
    read_doc_blocks,
    remember_version,
    restore_version,
    save_doc_blocks,
)


def _write(root: Path, text: str) -> Path:
    tools = {t.__name__: t for t in build_document_tools(root)}  # type: ignore[attr-defined]
    tools["write_docx"](path="d.docx", content=f"# T\n\n{text}\n")
    return root / "d.docx"


def _sources(state: Path, path: Path) -> list[str]:
    folder = history._folder_of(path, state)
    return [e["source"] for e in json.loads((folder / "index.json").read_text())]


def _edit(path: Path, text: str) -> None:
    read = read_doc_blocks(path)
    blocks: list[dict[str, Any]] = read["blocks"]
    blocks[1]["runs"] = [{"t": text}]
    save_doc_blocks(path, read["version"], blocks)


def test_the_persons_saves_are_one_step_and_a_change_behind_the_editor_is_another(
    tmp_path: Path,
) -> None:
    state = tmp_path / "state"
    path = _write(tmp_path, "one")
    first = remember_version(path, state, "seen")
    for text in ("two", "three"):
        _edit(path, text)
        remember_version(path, state, "you")
    assert _sources(state, path) == ["seen", "you"]  # the opening version, and the typing since
    mine = remember_version(path, state, "you")

    _write(tmp_path, "behind")
    theirs = remember_version(path, state, "seen")
    assert _sources(state, path) == ["seen", "you", "seen"]
    assert len({first, mine, theirs}) == 3


def test_a_version_is_put_back_over_the_one_the_editor_holds_and_the_step_can_be_taken_back(
    tmp_path: Path,
) -> None:
    state = tmp_path / "state"
    path = _write(tmp_path, "one")
    before = remember_version(path, state, "seen")
    _write(tmp_path, "behind")
    after = remember_version(path, state, "seen")

    back = restore_version(path, state, after, before)
    assert back["version"] == before and read_doc_blocks(path)["version"] == before
    again = restore_version(path, state, before, after)
    assert again["version"] == after
    with pytest.raises(DocChanged):
        restore_version(path, state, before, after)  # the file is not the version it was told
    with pytest.raises(VersionGone):
        restore_version(path, state, after, "0" * 32)
    with pytest.raises(VersionGone):
        restore_version(path, state, after, "../x")


def test_only_the_last_twenty_versions_and_files_below_the_size_cap_are_kept(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    state = tmp_path / "state"
    path = _write(tmp_path, "start")
    for number in range(25):
        _write(tmp_path, f"change {number}")
        remember_version(path, state, "seen")
    folder = history._folder_of(path, state)
    assert len(json.loads((folder / "index.json").read_text())) == 20
    assert len(list(folder.glob("*.docx"))) == 20

    monkeypatch.setattr(history, "_MAX_BYTES", 10)
    _write(tmp_path, "too big to keep")
    remember_version(path, state, "seen")
    assert len(list(folder.glob("*.docx"))) == 20
