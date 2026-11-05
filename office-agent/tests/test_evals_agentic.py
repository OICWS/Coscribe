"""The deterministic parts of the multi-turn evaluation (`evals/agentic/`): the inputs, the
checks, the scripted user and the metrics. Nothing here calls a model."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import pytest
from docx import Document
from openpyxl import Workbook
from pptx import Presentation

from evals.agentic import run, tasks


def _outcome(tmp_path: Path, *replies: list[str], memory: str = "") -> tasks.Outcome:
    return tasks.Outcome(replies=list(replies), workspace=tmp_path, memory=memory)


@pytest.mark.parametrize("task", tasks.TASKS, ids=lambda t: t.name)
def test_every_task_sets_up_its_inputs_and_fails_its_checks_on_an_empty_answer(
    task: tasks.AgenticTask, tmp_path: Path
) -> None:
    task.setup(tmp_path)

    results = run.run_checks(task, _outcome(tmp_path, [""]))

    assert task.turns and task.checks
    assert not any(results.values())


def test_the_generated_inputs_hold_the_answers_the_checks_expect(tmp_path: Path) -> None:
    tasks.write_reports(tmp_path)
    tasks.write_notes(tmp_path)

    assert f"is {tasks.report_code(8)}." in (tmp_path / "report8.txt").read_text(encoding="utf-8")
    assert "Mei Lin" in (tmp_path / "report6.txt").read_text(encoding="utf-8")
    assert f"is {tasks.note_code(24)}." in (tmp_path / "note24.txt").read_text(encoding="utf-8")
    assert not any("zebra" in p.read_text(encoding="utf-8") for p in tmp_path.glob("*.txt"))


def test_the_order_totals_are_computed_from_the_file_the_task_writes(tmp_path: Path) -> None:
    tasks.write_orders(300)(tmp_path)
    rows = (tmp_path / "orders.csv").read_text(encoding="utf-8").splitlines()[1:]

    south = [int(r.split(",")[2]) for r in rows if r.split(",")[1] == "south"]

    assert len(rows) == 300
    assert tasks.region_totals(300)["south"] == sum(south)
    assert tasks.region_counts(300)["south"] == len(south)


def test_says_reads_only_the_last_turn_and_ignores_case_spaces_and_thousands_separators(
    tmp_path: Path,
) -> None:
    check = tasks.says("36037", "Mei Lin")

    assert check(_outcome(tmp_path, ["nothing"], ["The total is 36,037."]))
    assert check(_outcome(tmp_path, ["MEI  LIN owns it"]))
    assert not check(_outcome(tmp_path, ["36037"], ["no answer"]))


def test_remembered_reads_the_global_instructions(tmp_path: Path) -> None:
    check = tasks.remembered("YYYY-MM-DD")

    assert check(_outcome(tmp_path, [], memory="- Write dates as yyyy-mm-dd\n"))
    assert not check(_outcome(tmp_path, []))


def test_file_says_reads_word_excel_and_powerpoint_files(tmp_path: Path) -> None:
    document = Document()
    document.add_paragraph("East had the highest total: 37,977.")
    document.save(str(tmp_path / "region_memo.docx"))
    workbook = Workbook()
    workbook.active.append(["North", 1])
    workbook.save(tmp_path / "orders_summary.xlsx")
    deck = Presentation()
    slide = deck.slides.add_slide(deck.slide_layouts[1])
    slide.shapes.title.text = "East leads"
    deck.save(str(tmp_path / "region_deck.pptx"))
    (tmp_path / "broken.docx").write_text("not a document", encoding="utf-8")

    outcome = _outcome(tmp_path, [])

    assert tasks.file_says("region_memo*.docx", "east", "37977")(outcome)
    assert tasks.file_says("orders_summary*.xlsx", "north")(outcome)
    assert tasks.file_says("region_deck.pptx", "east")(outcome)
    assert not tasks.file_says("orders_summary*.xlsx", "south")(outcome)
    assert not tasks.file_says("broken.docx", "document")(outcome)


def test_select_takes_number_prefixes_and_rejects_an_unknown_task() -> None:
    chosen = [t.name for t in tasks.select("01,06")]

    assert chosen == ["01-plan-eight-reports", "06-two-deliverables"]
    assert len(tasks.select("all")) == len(tasks.TASKS)
    with pytest.raises(SystemExit):
        tasks.select("99")


def test_repeated_calls_count_the_same_arguments_again_in_the_same_turn_only() -> None:
    first = run.Turn(calls=[("read_file", '{"path": "a"}'), ("read_file", '{"path": "a"}')])
    second = run.Turn(calls=[("read_file", '{"path": "a"}'), ("read_file", '{"path": "b"}')])

    assert run.repeated_calls([first, second]) == {"read_file": 1}


def test_a_reply_with_the_compaction_headings_is_a_summary_leak() -> None:
    turns = [run.Turn(replies=["## Requests\n- read files\n## Current work\n- x", "Done."])]

    assert run.summary_leaks(turns) == 1
    assert run.open_tasks([{"status": "completed"}, {"status": "in_progress"}]) == 1


class _Session:
    def __init__(self) -> None:
        self.answers: list[Any] = []
        self.approved: list[str] = []

    def resolve_question(self, question_id: str, answers: Any) -> None:
        self.answers.append(answers)

    def resolve_approval(self, approval_id: str, approved: bool) -> None:
        self.approved.append(approval_id)


def test_the_scripted_user_saves_a_remember_offer_and_records_calls_per_turn() -> None:
    session = _Session()
    user = run.ScriptedUser(session=session, can_resolve_approvals=True)
    user.turns.append(run.Turn())
    remember = {"question": 'Save "x" to your global instructions? They are read in every...'}
    events = [
        {"type": "tool_started", "tool_name": "remember", "arguments": {"line": "x"}},
        {"type": "question_required", "id": "q1", "questions": [remember]},
        {"type": "question_required", "id": "q2", "questions": [{"question": "Which one?"}]},
        {"type": "approval_required", "id": "a1"},
        {"type": "agent_message", "text": "Saved."},
    ]

    for event in events:
        asyncio.run(user.send_json(event))

    assert session.answers[0] == ["Save"]
    assert "Decide it yourself" in session.answers[1][0]
    assert session.approved == ["a1"]
    assert (user.saves, user.questions, user.approvals) == (1, 2, 1)
    assert user.turns[0].calls == [("remember", json.dumps({"line": "x"}))]
    assert user.turns[0].replies == ["Saved."]


def _result(name: str, completed: bool, after: bool | None, cost: float | None) -> dict[str, Any]:
    return {
        "task": name,
        "completed": completed,
        "completed_after_nudge": after,
        "open_tasks_at_end": 1,
        "repeated_calls": {"read_file": 2},
        "summary_leaks": 0,
        "questions": 1,
        "approvals": 0,
        "tool_call_count": 5,
        "tool_errors": [],
        "wall_seconds": 10.0,
        "cost": cost,
    }


def test_the_summary_counts_completion_with_and_without_a_nudge(tmp_path: Path) -> None:
    results = [_result("01-a", True, None, 0.01), _result("02-b", False, True, None)]

    text = run.write_summary(tmp_path, results)
    totals = json.loads((tmp_path / "summary.json").read_text(encoding="utf-8"))["totals"]

    assert totals["completed"] == 1
    assert totals["completed_after_nudge"] == 1
    assert totals["needed_a_nudge"] == 1
    assert totals["repeated_calls"] == 4
    assert totals["cost"] == 0.01
    assert "| 02-b | no | yes |" in text
    assert "Completed 1/2 without help, 1 more after one nudge" in text
