"""The folder brief: what the side model reads, where the brief is kept and when it is written."""

import asyncio
from pathlib import Path
from typing import Any

import pytest

pytest.importorskip("langgraph", reason="needs the langgraph_spike extra installed")

from langchain_core.messages import AIMessage

from coscribe.conversation.folder_brief import (
    MAX_BRIEF_CHARS,
    FolderBriefKeeper,
    FolderBriefs,
    clean_brief,
    folder_listing,
    top_signature,
)


class _Model:
    def __init__(self, reply: str = "Monthly sales reports.") -> None:
        self.reply = reply
        self.calls: list[list[Any]] = []

    async def ainvoke(self, messages: list[Any], config: Any = None) -> AIMessage:
        self.calls.append(messages)
        return AIMessage(content=self.reply)


def _folder(tmp_path: Path) -> Path:
    root = tmp_path / "Sales"
    (root / "templates").mkdir(parents=True)
    (root / "2026" / "Q1").mkdir(parents=True)
    (root / "templates" / "report.docx").write_text("x")
    (root / "2026" / "jan.xlsx").write_text("secret figures")
    (root / "2026" / "feb.xlsx").write_text("x")
    (root / "readme.txt").write_text("x")
    (root / ".git").mkdir()
    (root / ".git" / "HEAD").write_text("x")
    (root / "~$jan.xlsx").write_text("lock")
    return root


def test_listing_counts_types_two_levels_deep_and_reads_no_file(tmp_path: Path) -> None:
    listing, signature = folder_listing(_folder(tmp_path))

    assert listing.splitlines() == [
        "(top): 1 files (1 .txt); e.g. readme.txt",
        "2026/: 2 files (2 .xlsx); e.g. feb.xlsx, jan.xlsx; subfolders: Q1",
        "templates/: 1 files (1 .docx); e.g. report.docx",
    ]
    assert "secret" not in listing and ".git" not in listing and "~$" not in listing
    assert signature == top_signature(tmp_path / "Sales")


def test_signature_changes_with_the_top_names_only(tmp_path: Path) -> None:
    root = _folder(tmp_path)
    before = top_signature(root)
    (root / "2026" / "mar.xlsx").write_text("x")
    assert top_signature(root) == before
    (root / "archive").mkdir()
    assert top_signature(root) != before


def test_clean_brief_joins_lines_and_cuts_at_a_word() -> None:
    assert clean_brief(" A folder.\n\n It holds  files. ") == "A folder. It holds files."
    cut = clean_brief("word " * 400)
    assert len(cut) <= MAX_BRIEF_CHARS + 3 and cut.endswith("word...")


def test_briefs_are_kept_per_folder(tmp_path: Path) -> None:
    briefs = FolderBriefs(tmp_path / "state")
    briefs.save(tmp_path / "a", "First.", "s1")
    briefs.save(tmp_path / "b", "Second.", "s2")

    again = FolderBriefs(tmp_path / "state")
    assert (again.get(tmp_path / "a") or {})["brief"] == "First."
    assert (again.get(tmp_path / "b") or {})["signature"] == "s2"
    assert again.get(tmp_path / "c") is None


def _keeper(tmp_path: Path, model: _Model, enabled: bool = True) -> FolderBriefKeeper:
    return FolderBriefKeeper(tmp_path / "state", lambda: model, lambda: enabled)


async def test_context_carries_the_brief_from_the_next_message_on(tmp_path: Path) -> None:
    root = _folder(tmp_path)
    model = _Model()
    keeper = _keeper(tmp_path, model)

    # The first message goes without it rather than wait for the side model.
    assert keeper.context("Folders: Sales", [root]) == "Folders: Sales"
    await asyncio.gather(*keeper._writing.values())

    assert keeper.context("Folders: Sales", [root]) == (
        "Folders: Sales\n\nWhat the folders hold, from their file names:\n"
        f"- Sales ({root}): Monthly sales reports."
    )
    assert len(model.calls) == 1
    assert "Folder: Sales\n(top): 1 files" in model.calls[0][1].content


async def test_brief_is_written_again_when_the_top_changes(tmp_path: Path) -> None:
    root = _folder(tmp_path)
    model = _Model()
    keeper = _keeper(tmp_path, model)
    await asyncio.gather(*keeper.refresh([root]))
    assert keeper.refresh([root]) == []

    (root / "drafts").mkdir()
    await asyncio.gather(*keeper.refresh([root]))
    assert len(model.calls) == 2


async def test_empty_folder_gets_no_brief_and_no_call(tmp_path: Path) -> None:
    (tmp_path / "empty").mkdir()
    model = _Model()
    keeper = _keeper(tmp_path, model)
    await asyncio.gather(*keeper.refresh([tmp_path / "empty"]))

    assert model.calls == []
    assert keeper.shown([tmp_path / "empty"])[0]["brief"] == ""


async def test_turned_off_only_read_again_writes(tmp_path: Path) -> None:
    root = _folder(tmp_path)
    model = _Model()
    keeper = _keeper(tmp_path, model, enabled=False)
    assert keeper.refresh([root]) == []

    shown = await keeper.reread(root)
    assert shown["brief"] == "Monthly sales reports." and shown["writing"] is False
    assert shown["name"] == "Sales" and shown["written_at"]


async def test_a_failed_call_leaves_the_folder_without_a_brief(tmp_path: Path) -> None:
    class _Failing(_Model):
        async def ainvoke(self, messages: list[Any], config: Any = None) -> AIMessage:
            raise RuntimeError("no key")

    root = _folder(tmp_path)
    keeper = _keeper(tmp_path, _Failing())
    shown = await keeper.reread(root)
    assert shown["brief"] == "" and shown["written_at"] is None
    # Not tried again each time the panel asks, only once the folder changes or on "Read again".
    assert shown["writing"] is False and keeper.refresh([root]) == []
    (root / "new").mkdir()
    assert len(keeper.refresh([root])) == 1


async def test_the_side_panel_asking_starts_a_missing_brief(tmp_path: Path) -> None:
    root = _folder(tmp_path)
    model = _Model()
    keeper = _keeper(tmp_path, model)

    assert keeper.shown([root])[0]["writing"] is True
    await asyncio.gather(*keeper._writing.values())
    assert keeper.shown([root])[0]["brief"] == "Monthly sales reports."
