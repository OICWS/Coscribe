"""The parts of the public-benchmark runner that need no model, no LibreOffice and no download:
how tasks are read, which files count as the agent's answer, and how a verifier's report becomes
a score."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from evals import external


@pytest.mark.parametrize(
    ("report", "expected"),
    [
        ({"status": "ok", "dim1_pass": False, "total_score": 40, "max_score": 50}, 0.0),
        ({"status": "ok", "dim1_pass": True, "total_score": -5, "max_score": 50}, 0.0),
        ({"status": "ok", "dim1_pass": True, "total_score": 42, "max_score": 56}, 0.75),
        ({"status": "ok", "dim1_pass": True, "total_score": 3}, None),
        ({"status": "error", "total_score": True, "max_score": 10}, None),
        ({"status": "ok", "dim1_pass": True, "total_score": 3, "max_score": 0}, None),
    ],
)
def test_an_officeval_report_scores_as_the_benchmark_counts_it(report, expected):
    assert external.officeval_fraction(report) == expected


def test_only_office_files_the_agent_made_or_changed_count(tmp_path: Path):
    kept = tmp_path / "input.xlsx"
    kept.write_bytes(b"original")
    edited = tmp_path / "report.docx"
    edited.write_bytes(b"before")
    originals = {
        "input.xlsx": hashlib.sha256(b"original").hexdigest(),
        "report.docx": hashlib.sha256(b"before").hexdigest(),
    }
    edited.write_bytes(b"after")
    (tmp_path / "out").mkdir()
    (tmp_path / "out" / "new.pptx").write_bytes(b"deck")
    (tmp_path / "~$report.docx").write_bytes(b"lock")
    (tmp_path / "notes.txt").write_text("not office")

    found = external.changed_files(tmp_path, originals, external.OFFICE_SUFFIXES)

    assert [p.relative_to(tmp_path).as_posix() for p in found] == ["out/new.pptx", "report.docx"]


def test_officeval_tasks_read_the_instruction_and_the_inputs(tmp_path: Path):
    (tmp_path / "tasks").mkdir()
    spec = {
        "id": "officeval_003",
        "instruction": "Add a total row.",
        "origin_files": [{"dest": "sales.xlsx"}],
    }
    (tmp_path / "tasks" / "officeval_003.json").write_text(json.dumps(spec), "utf-8")
    folder = tmp_path / "task_files" / "officeval_003"
    folder.mkdir(parents=True)
    (folder / "sales.xlsx").write_bytes(b"x")

    [task] = external.officeval_tasks(tmp_path, tmp_path, ["003"], "python")

    assert task.name == "officeval_003"
    assert task.inputs == [folder / "sales.xlsx"]
    assert "Add a total row." in task.brief


def test_an_officeval_task_whose_files_are_missing_is_refused(tmp_path: Path):
    (tmp_path / "tasks").mkdir()
    spec = {"id": "officeval_004", "instruction": "x", "origin_files": [{"dest": "a.docx"}]}
    (tmp_path / "tasks" / "officeval_004.json").write_text(json.dumps(spec), "utf-8")

    with pytest.raises(FileNotFoundError, match="not downloaded"):
        external.officeval_tasks(tmp_path, tmp_path, ["004"], "python")


def test_a_spreadsheet_task_names_the_sheet_of_its_answer(tmp_path: Path):
    entries = [
        {
            "id": 45738,
            "instruction": "Sum column B.",
            "spreadsheet_path": "spreadsheet/45738",
            "instruction_type": "Cell-Level Manipulation",
            "answer_position": "C2:C10",
            "answer_sheet": "Data",
        },
        {
            "id": "41-47",
            "instruction": "Fill D.",
            "spreadsheet_path": "spreadsheet/41-47",
            "instruction_type": "Sheet-Level Manipulation",
            "answer_position": "'Sheet1'!D1:D4",
            "answer_sheet": "Sheet1",
        },
    ]
    (tmp_path / "dataset.json").write_text(json.dumps(entries), "utf-8")

    first, second = external.spreadsheet_tasks(tmp_path, tmp_path, ["45738", "41-47"], "python")

    assert first.name == "sb-45738"
    assert first.inputs == [tmp_path / "spreadsheet/45738/1_45738_init.xlsx"]
    assert "'Data'!C2:C10" in first.brief
    assert "output.xlsx" in first.brief
    assert "'Sheet1'!D1:D4" in second.brief
    assert "''Sheet1'" not in second.brief


def test_a_summary_averages_only_the_graded_tasks():
    rows = [
        {
            "task": "a",
            "status": "ok",
            "score_fraction": 1.0,
            "cost": 0.02,
            "wall_seconds": 10,
            "model_calls": 3,
        },
        {
            "task": "b",
            "status": "ok",
            "score_fraction": 0.5,
            "cost": 0.04,
            "wall_seconds": 20,
            "model_calls": 5,
        },
        {
            "task": "c",
            "status": "error",
            "score_fraction": None,
            "cost": None,
            "wall_seconds": 1,
            "model_calls": 0,
        },
    ]

    summary = external.summarize(rows)

    assert summary["tasks"] == 3
    assert summary["graded"] == 2
    assert summary["mean_score"] == 0.75
    assert summary["total_cost"] == 0.06
    assert summary["cost_per_task"] == 0.03
    assert [r["task"] for r in summary["rows"]] == ["a", "b", "c"]
