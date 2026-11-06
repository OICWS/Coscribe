"""The turn-end check that opens the Word, Excel and PowerPoint files a turn wrote."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path
from typing import Any

from docx import Document
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command
from openpyxl import Workbook
from pptx import Presentation

from coscribe.runtime import tool_metadata
from coscribe.runtime_lg.agent import build_langgraph_agent
from coscribe.runtime_lg.delivery_check import why_it_does_not_open, written_office_files
from coscribe.runtime_lg.messages import is_plan_check

from .test_turn_checks import _call, _Model


def _good_files(folder: Path) -> list[Path]:
    document = Document()
    document.add_paragraph("memo")
    document.save(str(folder / "memo.docx"))
    workbook = Workbook()
    workbook.active.append(["north", 1])
    workbook.save(folder / "totals.xlsx")
    Presentation().save(str(folder / "deck.pptx"))
    return [folder / "memo.docx", folder / "totals.xlsx", folder / "deck.pptx"]


def test_word_excel_and_powerpoint_files_that_open_pass(tmp_path: Path) -> None:
    assert [why_it_does_not_open(p) for p in _good_files(tmp_path)] == [None, None, None]


def test_a_file_that_is_not_a_package_or_lacks_its_main_part_does_not_open(
    tmp_path: Path,
) -> None:
    good = _good_files(tmp_path)[1]
    text = tmp_path / "memo.docx"
    text.write_text("not a document", encoding="utf-8")

    hollow = tmp_path / "hollow.xlsx"
    with zipfile.ZipFile(good) as source, zipfile.ZipFile(hollow, "w") as target:
        for item in source.infolist():
            if item.filename != "xl/workbook.xml":
                target.writestr(item, source.read(item))

    assert "BadZipFile" in (why_it_does_not_open(text) or "")
    assert why_it_does_not_open(hollow)


def test_the_files_named_by_writing_calls_and_by_a_scripts_result_are_collected() -> None:
    turn = [
        _call("c1", "write_file", path="a.docx", content="x"),
        _call("c2", "read_file", path="b.xlsx"),
        AIMessage(
            content="",
            tool_calls=[
                {
                    "id": "c3",
                    "name": "use_tool",
                    "args": {"name": "write_file", "arguments": {"path": "c.PPTX"}},
                }
            ],
        ),
        ToolMessage(
            content=json.dumps({"stdout": "", "files_written": ["d.xlsx", "e.csv", "a.docx"]}),
            tool_call_id="c4",
        ),
        _call("c5", "write_file", path="theirs.docx", content="x"),
        ToolMessage(content="Error: refused", tool_call_id="c5", status="error"),
    ]

    assert written_office_files(turn, {"write_file"}) == ["a.docx", "c.PPTX", "d.xlsx"]


def write_file(path: str, content: str) -> str:
    """Writes a file."""
    Path(path).write_text(content, encoding="utf-8")
    return "written"


tool_metadata(write_file, risk_category="WRITE_LOCAL", category="filesystem")


def _run(model: _Model, folder: Path) -> Any:
    agent = build_langgraph_agent(
        model,
        [write_file],
        "be helpful",
        checkpointer=InMemorySaver(),
        resolve_file=lambda name: folder / name,
    )
    config: Any = {"configurable": {"thread_id": "t"}}
    result = agent.invoke({"messages": [HumanMessage(content="make a memo")]}, config=config)
    # Writing a file asks for approval; the person approves each one.
    while (tasks := agent.get_state(config).tasks) and tasks[0].interrupts:
        interrupt = tasks[0].interrupts[0]
        decisions = [{"type": "approve"} for _ in interrupt.value.get("action_requests", [])]
        result = agent.invoke(Command(resume={interrupt.id: {"decisions": decisions}}), config)
    return result


def test_a_turn_that_wrote_a_word_file_which_does_not_open_hears_it_once(tmp_path: Path) -> None:
    broken = str(tmp_path / "memo.docx")
    model = _Model(
        responses=[
            _call("c1", "write_file", path=broken, content="plain text"),
            AIMessage(content="Your memo is ready."),
            AIMessage(content="Sorry, the memo is broken."),
        ]
    )

    result = _run(model, tmp_path)

    notes = [m for m in result["messages"] if is_plan_check(m)]
    assert model.i == 3
    assert len(notes) == 1
    assert "memo.docx" in notes[0].content and "don't open" in notes[0].content
    assert result["messages"][-1].content == "Sorry, the memo is broken."


def test_a_turn_whose_office_files_open_or_that_wrote_none_ends_when_the_model_stops(
    tmp_path: Path,
) -> None:
    model = _Model(
        responses=[
            _call("c1", "write_file", path=str(tmp_path / "notes.txt"), content="x"),
            AIMessage(content="Done."),
        ]
    )

    result = _run(model, tmp_path)

    assert model.i == 2
    assert not any(is_plan_check(m) for m in result["messages"])
