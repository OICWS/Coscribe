"""The multi-turn tasks: what a person types, turn by turn, the files their folder holds, and what
the finished conversation must show. Inputs are generated from fixed seeds, so the expected
answers are computed here rather than stored."""

from __future__ import annotations

import csv
import random
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Sent once when a check fails after the scripted turns: the least a person would say.
NUDGE = "Is everything I asked for done? Please check and finish anything that is missing."

REPORT_NAMES = ("alpha", "bravo", "charlie", "delta", "echo", "foxtrot", "golf", "hotel")
REGIONS = ("north", "south", "east", "west")


@dataclass
class Outcome:
    """What a conversation left behind, for the checks to read."""

    replies: list[list[str]]
    workspace: Path
    memory: str = ""
    tasks: list[dict[str, Any]] = field(default_factory=list)

    def last_reply(self) -> str:
        return "\n".join(self.replies[-1]) if self.replies else ""


Check = Callable[[Outcome], bool]


@dataclass(frozen=True)
class AgenticTask:
    name: str
    turns: tuple[str, ...]
    setup: Callable[[Path], None]
    checks: dict[str, Check]
    # The share of the context window that starts a compaction: low values make a task's long
    # reads run through compaction and clearing the way a long real conversation does.
    compact_threshold: float = 0.8


def says(*alternatives: str) -> Check:
    """The last turn's replies hold one of the spellings (case and spaces are ignored)."""

    def check(outcome: Outcome) -> bool:
        reply = _squash(outcome.last_reply())
        return any(_squash(text) in reply for text in alternatives)

    return check


def remembered(text: str) -> Check:
    def check(outcome: Outcome) -> bool:
        return text.lower() in outcome.memory.lower()

    return check


def file_says(pattern: str, *texts: str) -> Check:
    """A file matching the pattern was written and its text holds every one of the texts."""

    def check(outcome: Outcome) -> bool:
        for path in outcome.workspace.glob(pattern):
            content = _squash(file_text(path))
            if all(_squash(text) in content for text in texts):
                return True
        return False

    return check


def file_text(path: Path) -> str:
    """The words a file shows, for Word and Excel files as well as plain text; an unreadable
    file is empty."""
    try:
        if path.suffix == ".docx":
            from docx import Document

            document = Document(str(path))
            cells = [c.text for t in document.tables for row in t.rows for c in row.cells]
            return "\n".join([p.text for p in document.paragraphs] + cells)
        if path.suffix == ".pptx":
            from pptx import Presentation

            shapes = [shape for slide in Presentation(str(path)).slides for shape in slide.shapes]
            return "\n".join(shape.text_frame.text for shape in shapes if shape.has_text_frame)
        if path.suffix == ".xlsx":
            from openpyxl import load_workbook

            workbook = load_workbook(path, data_only=False)
            values = [
                str(cell.value)
                for sheet in workbook.worksheets
                for row in sheet.iter_rows()
                for cell in row
                if cell.value is not None
            ]
            return "\n".join(workbook.sheetnames + values)
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001 -- a file the agent broke fails the check, not the run
        return ""


def _squash(text: str) -> str:
    return "".join(text.lower().replace(",", "").split())


# --- inputs ------------------------------------------------------------------------------


def report_code(number: int) -> int:
    return 1000 + number * 37


def write_reports(workspace: Path) -> None:
    rnd = random.Random(3)
    words = "revenue margin pipeline churn forecast headcount budget vendor audit roadmap".split()
    for i, name in enumerate(REPORT_NAMES, start=1):
        filler = " ".join(rnd.choice(words) for _ in range(3000))
        fact = f"The {name} code for report {i} is {report_code(i)}."
        extra = " Project Falcon is owned by Mei Lin in Suzhou." if i == 6 else ""
        (workspace / f"report{i}.txt").write_text(
            f"Report {i}\n{filler[:7000]}\n{fact}{extra}\n{filler[7000:14000]}\n", encoding="utf-8"
        )


def note_code(number: int) -> int:
    return 5000 + number * 13


def write_notes(workspace: Path) -> None:
    rnd = random.Random(5)
    words = "invoice ledger supplier shipment quota tariff rebate warehouse".split()
    for i in range(1, 25):
        filler = " ".join(rnd.choice(words) for _ in range(1100))
        (workspace / f"note{i:02d}.txt").write_text(
            f"Note {i}\n{filler[:3000]}\nThe code in note {i} is {note_code(i)}.\n"
            f"{filler[3000:6000]}\n",
            encoding="utf-8",
        )


def orders(count: int) -> list[tuple[int, str, int]]:
    rnd = random.Random(7)
    return [(i, rnd.choice(REGIONS), rnd.randint(1, 999)) for i in range(1, count + 1)]


def write_orders(count: int, name: str = "orders.csv") -> Callable[[Path], None]:
    def setup(workspace: Path) -> None:
        with (workspace / name).open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["row", "region", "amount"])
            writer.writerows(orders(count))

    return setup


def region_totals(count: int) -> Counter[str]:
    totals: Counter[str] = Counter()
    for _, region, amount in orders(count):
        totals[region] += amount
    return totals


def region_counts(count: int) -> Counter[str]:
    return Counter(region for _, region, _ in orders(count))


def biggest_order(count: int) -> tuple[int, str, int]:
    return max(orders(count), key=lambda order: order[2])


def write_twelve_notes(workspace: Path) -> None:
    write_notes(workspace)
    for i in range(13, 25):
        (workspace / f"note{i:02d}.txt").unlink()


def nothing(workspace: Path) -> None:
    del workspace


# --- the tasks ---------------------------------------------------------------------------

_BIG = 20000
_SMALL = 300
_TOP_REGION, _TOP_TOTAL = region_totals(_SMALL).most_common(1)[0]

TASKS: tuple[AgenticTask, ...] = (
    AgenticTask(
        name="01-plan-eight-reports",
        turns=(
            "First, create a task for each of the 8 files report1.txt to report8.txt. Then read "
            "each file in full, one per read_file call, in order, and mark its task done after "
            "reading it. Don't summarize yet.",
            "Now tell me the code given in report1.txt and the code given in report8.txt, exactly.",
        ),
        setup=write_reports,
        checks={
            "report1 code": says(str(report_code(1))),
            "report8 code": says(str(report_code(8))),
        },
        compact_threshold=0.03,
    ),
    AgenticTask(
        name="02-many-reads",
        turns=(
            "Read note01.txt to note24.txt in full, one read_file call per file, in order, and "
            "note each one's code. When all 24 are read, tell me the code in note01.txt and the "
            "code in note24.txt, quoting each sentence.",
        ),
        setup=write_notes,
        checks={
            "note01 code": says(str(note_code(1))),
            "note24 code": says(str(note_code(24))),
        },
        compact_threshold=0.05,
    ),
    AgenticTask(
        name="03-script-output",
        turns=(
            "Run a Python script that prints every row of orders.csv (all 20000 rows, one per "
            "line). Then, from that printed output, tell me the amount on row 15000 and the "
            "amount on row 19999.",
        ),
        setup=write_orders(_BIG),
        checks={
            "row 15000 amount": says(str(orders(_BIG)[14999][2])),
            "row 19999 amount": says(str(orders(_BIG)[19998][2])),
        },
    ),
    AgenticTask(
        name="04-delegate-research",
        turns=(
            "Delegate this to a research sub-agent: find which of the report*.txt files in this "
            "folder mention 'Project Falcon' and who owns it. Report the answer with the file "
            "name.",
        ),
        setup=write_reports,
        checks={"file": says("report6"), "owner": says("Mei Lin")},
    ),
    AgenticTask(
        name="05-remember-preference",
        turns=(
            "From now on, always write dates as YYYY-MM-DD in anything you make for me. Please "
            "remember this for all future conversations, not just this one.",
        ),
        setup=nothing,
        checks={"saved": remembered("YYYY-MM-DD")},
    ),
    AgenticTask(
        name="06-two-deliverables",
        turns=(
            "From orders.csv, make an Excel workbook orders_summary.xlsx with the total amount per "
            "region, and a short Word memo region_memo.docx that names the region with the highest "
            "total and gives that total.",
        ),
        setup=write_orders(_SMALL),
        checks={
            "workbook": file_says("orders_summary*.xlsx", *REGIONS),
            "memo": file_says("region_memo*.docx", _TOP_REGION, str(_TOP_TOTAL)),
        },
    ),
    AgenticTask(
        name="07-follow-up-correction",
        turns=(
            "What is the total amount for the north region in orders.csv?",
            "Sorry, I meant the south region. Give me its total and how many orders it has.",
        ),
        setup=write_orders(_SMALL),
        checks={
            "south total": says(str(region_totals(_SMALL)["south"])),
            "south count": says(str(region_counts(_SMALL)["south"])),
        },
    ),
    AgenticTask(
        name="08-nothing-to-find",
        turns=("Which file in this folder mentions a zebra? Quote the sentence.",),
        setup=write_reports,
        checks={
            "says none": says(
                "no file",
                "none of",
                "not mention",
                "doesn't mention",
                "don't mention",
                "no mention",
                "not found",
                "couldn't find",
                "could not find",
                "没有",
                "未找到",
            ),
        },
    ),
    AgenticTask(
        name="09-five-deliverables",
        turns=(
            "From orders.csv, make all of these: region_totals.xlsx with the total amount per "
            "region; region_memo.docx, a short memo naming the region with the highest total and "
            "that total; region_deck.pptx, three slides on the regions that name the top one; "
            "top_orders.csv with the 10 largest orders; and summary.md giving the total of all "
            "orders.",
        ),
        setup=write_orders(_SMALL),
        checks={
            "workbook": file_says("region_totals*.xlsx", *REGIONS),
            "memo": file_says("region_memo*.docx", _TOP_REGION, str(_TOP_TOTAL)),
            "deck": file_says("region_deck*.pptx", _TOP_REGION),
            "top orders": file_says("top_orders*.csv", str(biggest_order(_SMALL)[2])),
            "summary": file_says("summary*.md", str(sum(region_totals(_SMALL).values()))),
        },
    ),
    AgenticTask(
        name="10-twelve-files",
        turns=(
            "For each of note01.txt to note12.txt, find the code it gives and add a line "
            "'noteNN: CODE' to codes.txt (create it). Make a task for each file first, and read "
            "each file in full with its own read_file call.",
        ),
        setup=write_twelve_notes,
        checks={
            f"note{i:02d}": file_says("codes.txt", f"note{i:02d}:{note_code(i)}")
            for i in range(1, 13)
        },
        compact_threshold=0.05,
    ),
    AgenticTask(
        name="11-misnamed-file",
        turns=("What is the total amount in q3_sales.csv?",),
        setup=write_orders(50, "q3_sales_final.csv"),
        checks={"total": says(str(sum(region_totals(50).values())))},
    ),
)


def select(names: str) -> list[AgenticTask]:
    """`all`, or task names / number prefixes, comma-separated."""
    if names == "all":
        return list(TASKS)
    wanted = [n.strip() for n in names.split(",") if n.strip()]
    chosen = [t for t in TASKS if any(t.name == w or t.name.startswith(f"{w}-") for w in wanted)]
    if len(chosen) < len(wanted):
        raise SystemExit(f"unknown task in {names!r}; tasks: {[t.name for t in TASKS]}")
    return chosen
