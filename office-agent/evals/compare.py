"""Two runs side by side, as one Markdown table.

    python -m evals.compare evals/runs/baseline evals/runs/engine [--out compare.md]

For every task: the judge's scores (mean and spread over its rounds), the automatic checks, cost
and time, each run next to the other. A task one run lacks shows `-`; the total row sums, and the
mean row averages, only the tasks both runs have, so a run with fewer tasks does not look cheaper.
Scores come from one judge (`--judge`) and one kind of request: each deck alone (default) or the
two runs judged together (`--joint`, made by `evals.judge runA runB`).
"""

from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path
from typing import Any

from .judge import DEFAULT_JUDGE, DIMENSIONS, aggregate_scores, load_records
from .tasks import discover


def _read(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _load(run: Path, task: str, judge: str, joint_with: list[Path] | None) -> dict[str, Any] | None:
    """What the run has for the task, however little: a task that stopped half-way still
    counts in the table, with `-` where a file is missing."""
    folder = run / task
    result, checks = _read(folder / "result.json"), _read(folder / "checks.json")
    scores = aggregate_scores(load_records(run, task, judge, joint_with))
    if not (result or checks or scores):
        return None
    return {"result": result, "checks": checks, "scores": scores}


def _score(entry: dict[str, Any] | None, dimension: str) -> str:
    stats = (entry or {}).get("scores", {}).get(dimension)
    return "-" if not stats else f"{stats['mean']:.2f} ±{stats['spread']:.2f} (n={int(stats['n'])})"


def _mean_score(entries: list[dict[str, Any] | None], dimension: str) -> float | None:
    values = [e["scores"][dimension]["mean"] for e in entries if e and dimension in e["scores"]]
    return statistics.fmean(values) if values else None


def _facts(entry: dict[str, Any] | None) -> str:
    facts = (entry or {}).get("checks", {}).get("facts")
    return "-" if not facts else f"{facts.get('found', '-')}/{facts.get('total', '-')}"


def _passed(entry: dict[str, Any] | None, check: str) -> str:
    report = (entry or {}).get("checks", {}).get(check)
    return "-" if report is None else ("yes" if report.get("ok") else "NO")


def _layout(entry: dict[str, Any] | None) -> str:
    layout = (entry or {}).get("checks", {}).get("layout")
    if not layout or "error" in layout:
        return "-"
    return f"{layout.get('overflow_words') or 0} / {layout.get('text_overlaps', '-')}"


def _inventions(entry: dict[str, Any] | None) -> str:
    report = (entry or {}).get("checks", {}).get("inventions")
    return "-" if report is None else str(report.get("count", "-"))


def _money(entry: dict[str, Any] | None) -> str:
    cost = (entry or {}).get("result", {}).get("cost")
    return "-" if cost is None else f"{cost:.4f}"


def _seconds(entry: dict[str, Any] | None) -> str:
    seconds = (entry or {}).get("result", {}).get("wall_seconds")
    return "-" if seconds is None else f"{seconds:.0f}"


def _calls(entry: dict[str, Any] | None) -> str:
    calls = (entry or {}).get("result", {}).get("tool_call_count")
    return "-" if calls is None else str(calls)


def _tokens(entry: dict[str, Any] | None) -> str:
    r = (entry or {}).get("result", {})
    if "input_tokens" not in r or "output_tokens" not in r:
        return "-"
    cached = r.get("cached_tokens")
    shown = "" if cached is None else f" ({cached // 1000}k cached)"
    return f"{r['input_tokens'] // 1000}k{shown} / {r['output_tokens'] // 1000}k"


def _table(title: str, header: list[str], rows: list[list[str]]) -> list[str]:
    lines = [f"### {title}", "", "| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    lines += ["| " + " | ".join(row) + " |" for row in rows]
    return [*lines, ""]


def column_names(run_a: Path, run_b: Path) -> tuple[str, str]:
    """The folder names, or `parent/name` when those are equal (`engine` and `engine`)."""
    a, b = run_a.resolve(), run_b.resolve()
    if a.name != b.name:
        return a.name, b.name
    if a.parent.name != b.parent.name:
        return f"{a.parent.name}/{a.name}", f"{b.parent.name}/{b.name}"
    return f"A {a.name}", f"B {b.name}"


def _recalculated(entry: dict[str, Any] | None) -> str:
    recalc = (entry or {}).get("checks", {}).get("recalc")
    if recalc is None:
        return "-"
    return f"{'yes' if recalc.get('ok') else 'NO'} ({recalc.get('errors') or 0} errors)"


def _cells(entry: dict[str, Any] | None) -> str:
    cells = (entry or {}).get("checks", {}).get("cells")
    return "-" if not cells else f"{cells.get('matched', '-')}/{cells.get('checked', '-')}"


# The automatic-checks table: a column pair (run A, run B) per entry, by kind.
CHECK_COLUMNS: dict[str, list[tuple[str, Any]]] = {
    "pptx": [
        ("facts", _facts),
        ("pages", lambda e: _passed(e, "pages")),
        ("editable", lambda e: _passed(e, "editability")),
        ("numbers not in input", _inventions),
        ("overflow / overlaps", _layout),
    ],
    "xlsx": [
        ("facts", _facts),
        ("recalculates", _recalculated),
        ("cells", _cells),
        ("formulas", lambda e: _passed(e, "formulas")),
        ("probe", lambda e: _passed(e, "probe")),
        ("styles kept", lambda e: _passed(e, "untouched")),
        ("used range", lambda e: _passed(e, "used_range")),
        ("legible", lambda e: _passed(e, "legibility")),
        ("numbers not in input", _inventions),
    ],
}


def compare(
    run_a: Path, run_b: Path, judge: str = DEFAULT_JUDGE, joint: bool = False, kind: str = "pptx"
) -> str:
    names = [t.name for t in discover("all", kind=kind)]
    joint_with = [run_a, run_b] if joint else None
    pairs = [
        (n, _load(run_a, n, judge, joint_with), _load(run_b, n, judge, joint_with)) for n in names
    ]
    pairs = [p for p in pairs if p[1] is not None or p[2] is not None]
    a, b = column_names(run_a, run_b)
    common = [(n, ea, eb) for n, ea, eb in pairs if ea is not None and eb is not None]
    request = "both files in one request" if joint else "each file alone"
    out = [
        f"## {a} vs {b}",
        "",
        f"Judge {judge}, {request}; {len(common)} of {len(pairs)} tasks in both.",
        "",
    ]

    rows = []
    for name, ea, eb in pairs:
        rows.append([name] + [x for d in DIMENSIONS for x in (_score(ea, d), _score(eb, d))])
    mean_row = [f"**mean ({len(common)} common tasks)**"]
    for d in DIMENSIONS:
        for entries in ([e for _, e, _ in common], [e for _, _, e in common]):
            mean = _mean_score(entries, d)
            mean_row.append("-" if mean is None else f"{mean:.2f}")
    rows.append(mean_row)
    header = ["task"] + [f"{d} {x}" for d in DIMENSIONS for x in (a, b)]
    out += _table("Blind judge scores (1 to 5, mean ± spread over rounds)", header, rows)

    columns = CHECK_COLUMNS[kind]
    checks = [[n, *(x for _, read in columns for x in (read(ea), read(eb)))] for n, ea, eb in pairs]
    header = ["task", *(f"{label} {run}" for label, _ in columns for run in (a, b))]
    out += _table("Automatic checks", header, checks)

    cost_rows = [
        [
            n,
            _money(ea),
            _money(eb),
            _seconds(ea),
            _seconds(eb),
            _calls(ea),
            _calls(eb),
            _tokens(ea),
            _tokens(eb),
        ]
        for n, ea, eb in pairs
    ]

    def total(entries: list[dict[str, Any] | None], key: str) -> float:
        return sum((e["result"].get(key) or 0) for e in entries if e)

    entries_a, entries_b = [e for _, e, _ in common], [e for _, _, e in common]
    cost_rows.append(
        [
            f"**total ({len(common)} common tasks)**",
            f"{total(entries_a, 'cost'):.4f}",
            f"{total(entries_b, 'cost'):.4f}",
            f"{total(entries_a, 'wall_seconds'):.0f}",
            f"{total(entries_b, 'wall_seconds'):.0f}",
            f"{total(entries_a, 'tool_call_count'):.0f}",
            f"{total(entries_b, 'tool_call_count'):.0f}",
            "",
            "",
        ]
    )
    header = [
        "task",
        f"cost {a}",
        f"cost {b}",
        f"seconds {a}",
        f"seconds {b}",
        f"tool calls {a}",
        f"{b}",
        f"tokens in / out {a}",
        f"{b}",
    ]
    out += _table("Cost and time", header, cost_rows)
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("run_a", type=Path)
    parser.add_argument("run_b", type=Path)
    parser.add_argument("--out", type=Path, help="write the table here as well")
    parser.add_argument("--kind", choices=sorted(CHECK_COLUMNS), default="pptx", help="which tasks")
    parser.add_argument("--judge", default=DEFAULT_JUDGE, help="whose scores to show")
    parser.add_argument(
        "--joint", action="store_true", help="scores from the two runs judged in one request"
    )
    args = parser.parse_args(argv)
    table = compare(args.run_a, args.run_b, args.judge, args.joint, args.kind)
    if args.out:
        args.out.write_text(table, encoding="utf-8")
    print(table)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
