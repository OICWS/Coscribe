"""A Doc on disk (decision 0025): read for the editor, saved as edits to named blocks, the versions
it keeps in its side folder, and what the person changed since coscribe was told."""

from __future__ import annotations

from pathlib import Path

import pytest

from coscribe.tools.office.doc import (
    BlocksRefused,
    DocFileChanged,
    DocVersionGone,
    NotADoc,
    doc_edits_since_told,
    read_doc_file,
    remember_doc_before_edit,
    remember_doc_version,
    restore_doc_version,
    save_doc_edits,
)

SOURCE = "---\ncoscribe: doc\ntitle: Plan\n---\n\n# Plan\n\nFirst paragraph.\n\n- one\n- two\n"


def _doc(tmp_path: Path, text: str = SOURCE) -> Path:
    path = tmp_path / "plan.md"
    path.write_text(text, encoding="utf-8")
    return path


def test_the_doc_is_read_with_its_version_title_and_blocks(tmp_path: Path) -> None:
    read = read_doc_file(_doc(tmp_path))

    assert read["title"] == "Plan"
    assert [(b["index"], b["kind"]) for b in read["blocks"]] == [
        (0, "heading"),
        (1, "paragraph"),
        (2, "list"),
    ]
    assert len(read["version"]) == 32


def test_the_title_falls_back_to_the_first_heading_then_the_file_name(tmp_path: Path) -> None:
    assert read_doc_file(_doc(tmp_path, "---\ncoscribe: doc\n---\n\n# Heading\n"))["title"] == (
        "Heading"
    )
    assert read_doc_file(_doc(tmp_path, "---\ncoscribe: doc\n---\n\ntext\n"))["title"] == "plan"


def test_a_markdown_file_without_the_marker_is_not_a_doc(tmp_path: Path) -> None:
    with pytest.raises(NotADoc):
        read_doc_file(_doc(tmp_path, "# Just notes\n"))


def test_saving_applies_the_edits_to_the_version_that_was_read(tmp_path: Path) -> None:
    path = _doc(tmp_path)
    read = read_doc_file(path)

    saved = save_doc_edits(
        path,
        read["version"],
        [
            {"op": "replace", "index": 1, "expected": "First paragraph.", "text": "Reworded."},
            {"op": "insert", "after": 2, "text": "The end."},
        ],
    )

    assert path.read_text(encoding="utf-8") == SOURCE.replace("First paragraph.", "Reworded.") + (
        "\nThe end.\n"
    )
    assert saved["version"] != read["version"]
    assert saved["blocks"][-1]["text"] == "The end."


def test_a_save_over_a_file_that_changed_since_it_was_read_is_refused(tmp_path: Path) -> None:
    path = _doc(tmp_path)
    read = read_doc_file(path)
    path.write_text(SOURCE + "\nAdded by coscribe.\n", encoding="utf-8")

    with pytest.raises(DocFileChanged):
        save_doc_edits(path, read["version"], [{"op": "delete", "index": 0, "expected": "# Plan"}])

    assert "Added by coscribe." in path.read_text(encoding="utf-8")


@pytest.mark.parametrize(
    "edit",
    [
        "not an object",
        {"op": "move"},
        {"op": "replace", "index": 1},
        {"op": "replace", "index": "x", "expected": "a", "text": "b"},
        {"op": "replace", "index": 1, "expected": "wrong", "text": "b"},
        {"op": "delete", "index": 40, "expected": "a"},
    ],
)
def test_an_edit_that_cannot_apply_is_refused_and_nothing_is_written(
    tmp_path: Path, edit: object
) -> None:
    path = _doc(tmp_path)

    with pytest.raises(BlocksRefused):
        save_doc_edits(path, read_doc_file(path)["version"], [edit])

    assert path.read_text(encoding="utf-8") == SOURCE


def test_a_file_that_is_not_text_is_a_value_error(tmp_path: Path) -> None:
    path = tmp_path / "bad.md"
    path.write_bytes(b"\xff\xfe\x00bad")

    with pytest.raises(ValueError):
        read_doc_file(path)


def test_versions_are_kept_in_the_side_folder_and_one_can_be_put_back(tmp_path: Path) -> None:
    path = _doc(tmp_path)
    first = remember_doc_version(path, "seen")
    path.write_text(SOURCE + "\nBehind the editor.\n", encoding="utf-8")
    second = remember_doc_version(path, "seen")

    restored = restore_doc_version(path, second, first)

    assert path.read_text(encoding="utf-8") == SOURCE
    assert (tmp_path / "plan.doc" / "versions" / f"{first}.md").is_file()
    assert restored["version"] == first
    # The version that was replaced is kept, so the step can be taken back.
    again = restore_doc_version(path, first, second)
    assert "Behind the editor." in path.read_text(encoding="utf-8")
    assert again["version"] == second


def test_a_version_with_windows_line_endings_is_put_back_byte_for_byte(tmp_path: Path) -> None:
    """A Doc saved on Windows has CRLF; the version put back must be the very one asked for."""
    path = tmp_path / "plan.md"
    path.write_bytes(SOURCE.replace("\n", "\r\n").encode("utf-8"))
    first = remember_doc_version(path, "seen")
    path.write_bytes(path.read_bytes() + b"Behind the editor.\r\n")
    second = remember_doc_version(path, "seen")

    restored = restore_doc_version(path, second, first)

    assert restored["version"] == first
    assert path.read_bytes() == SOURCE.replace("\n", "\r\n").encode("utf-8")

def test_a_restore_over_a_newer_file_or_to_a_forgotten_version_is_refused(tmp_path: Path) -> None:
    path = _doc(tmp_path)
    held = remember_doc_version(path, "seen")
    with pytest.raises(DocVersionGone):
        restore_doc_version(path, held, "deadbeef")
    path.write_text(SOURCE + "\nNewer.\n", encoding="utf-8")
    with pytest.raises(DocFileChanged):
        restore_doc_version(path, held, held)


def test_the_persons_saves_are_one_step_and_only_twenty_versions_are_kept(tmp_path: Path) -> None:
    path = _doc(tmp_path)
    remember_doc_version(path, "seen")
    for n in range(3):
        path.write_text(SOURCE + f"\nedit {n}\n", encoding="utf-8")
        remember_doc_version(path, "you")
    folder = tmp_path / "plan.doc" / "versions"
    assert len(list(folder.glob("*.md"))) == 2

    for n in range(30):
        path.write_text(SOURCE + f"\nseen {n}\n", encoding="utf-8")
        remember_doc_version(path, "seen")
    assert len(list(folder.glob("*.md"))) == 20


def test_what_the_person_changed_is_told_once_and_an_undone_edit_is_not_told(
    tmp_path: Path,
) -> None:
    state = tmp_path / "state"
    path = _doc(tmp_path)
    assert doc_edits_since_told(path, state) is None

    remember_doc_before_edit(path, state)
    save_doc_edits(
        path,
        read_doc_file(path)["version"],
        [
            {
                "op": "replace",
                "index": 1,
                "expected": "First paragraph.",
                "text": "First, reworded.",
            },
            {"op": "insert", "after": 2, "text": "A new closing paragraph."},
            {"op": "delete", "index": 0, "expected": "# Plan"},
        ],
    )
    told = doc_edits_since_told(path, state)

    assert told is not None
    assert any("First paragraph." in c and "First, reworded." in c for c in told["changed"])
    assert any("A new closing paragraph." in a for a in told["added"])
    assert any("# Plan" in r for r in told["removed"])
    assert doc_edits_since_told(path, state) is None

    remember_doc_before_edit(path, state)
    version = read_doc_file(path)["version"]
    save_doc_edits(path, version, [{"op": "insert", "after": 0, "text": "Temporary."}])
    save_doc_edits(
        path,
        read_doc_file(path)["version"],
        [{"op": "delete", "index": 1, "expected": "Temporary."}],
    )
    assert doc_edits_since_told(path, state) is None
