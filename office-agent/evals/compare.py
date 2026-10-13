"""Two runs side by side, as one Markdown table.

    python -m evals.compare evals/runs/baseline evals/runs/engine [--out compare.md]

For every task: the judge's scores (mean and spread over its rounds), the automatic checks, cost
and time, each run next to the other. The totals row sums cost and time and averages the scores.
A task one run lacks shows `-`.
"""

from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path
from typing import Any

from .judge import DIMENSIONS, aggregate_scores, load_records
from .tasks import discover


def _load(run: Path, task: str) -> dict[str, Any] | None:
    result_path, checks_path = run / task / "result.json", run / task / "checks.json"
    if not (result_path.is_file() and checks_path.is_file()):
        return None
    return {
        "result": json.loads(result_path.read_text(encoding="utf-8")),
        "checks": json.loads(checks_path.read_text(encoding="utf-8")),
        "scores": aggregate_scores(load_records(run, task)),
    }


def _score(entry: dict[str, Any] | None, dimension: str) -> str:
    stats = (entry or {}).get("scores", {}).get(dimension)
    return "-" if not stats else f"{stats['mean']:.2f} ±{stats['spread']:.2f} (n={int(stats['n'])})"


def _mean_score(entries: list[dict[str, Any] | None], dimension: str) -> float | None:
    values = [e["scores"][dimension]["mean"] for e in entries if e and dimension in e["scores"]]
    return statistics.fmean(values) if values else None


def _facts(entry: dict[str, Any] | None) -> str:
    facts = (entry or {}).get("checks", {}).get("facts")
    return "-" if not facts else f"{facts['found']}/{facts['total']}"


def _passed(entry: dict[str, Any] | None, check: str) -> str:
    if entry is None:
        return "-"
    report = entry["checks"].get(check)
    return "-" if report is None else ("yes" if report.get("ok") else "NO")


def _layout(entry: dict[str, Any] | None) -> str:
    layout = (entry or {}).get("checks", {}).get("layout")
    if not layout or "error" in layout:
        return "-"
    return f"{layout['overflow_words'] or 0} / {layout['text_overlaps']}"


def _inventions(entry: dict[str, Any] | None) -> str:
    report = (entry or {}).get("checks", {}).get("inventions")
    return "-" if report is None else str(report["count"])


def _money(entry: dict[str, Any] | None) -> str:
    cost = (entry or {}).get("result", {}).get("cost")
    return "-" if cost is None else f"{cost:.4f}"


def _seconds(entry: dict[str, Any] | None) -> str:
    return "-" if entry is None else f"{entry['result']['wall_seconds']:.0f}"


def _calls(entry: dict[str, Any] | None) -> str:
    return "-" if entry is None else str(entry["result"]["tool_call_count"])


def _tokens(entry: dict[str, Any] | None) -> str:
    if entry is None:
        return "-"
    r = entry["result"]
    cached = r["cached_tokens"] // 1000
    return f"{r['input_tokens'] // 1000}k ({cached}k cached) / {r['output_tokens'] // 1000}k"


def _table(title: str, header: list[str], rows: list[list[str]]) -> list[str]:
    lines = [f"### {title}", "", "| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    lines += ["| " + " | ".join(row) + " |" for row in rows]
    return [*lines, ""]


def compare(run_a: Path, run_b: Path) -> str:
    names = [t.name for t in discover("all")]
    pairs = [(n, _load(run_a, n), _load(run_b, n)) for n in names]
    pairs = [p for p in pairs if p[1] is not None or p[2] is not None]
    a, b = run_a.name, run_b.name
    out = [f"## {a} vs {b}", ""]

    rows = []
    for name, ea, eb in pairs:
        rows.append([name] + [x for d in DIMENSIONS for x in (_score(ea, d), _score(eb, d))])
    mean_row = ["**mean**"]
    for d in DIMENSIONS:
        for entries in ([e for _, e, _ in pairs], [e for _, _, e in pairs]):
            mean = _mean_score(entries, d)
            mean_row.append("-" if mean is None else f"{mean:.2f}")
    rows.append(mean_row)
    header = ["task"] + [f"{d} {x}" for d in DIMENSIONS for x in (a, b)]
    out += _table("Blind judge scores (1 to 5, mean ± spread over rounds)", header, rows)

    checks = [
        [
            n,
            _facts(ea),
            _facts(eb),
            _passed(ea, "pages"),
            _passed(eb, "pages"),
            _passed(ea, "editability"),
            _passed(eb, "editability"),
            _inventions(ea),
            _inventions(eb),
            _layout(ea),
            _layout(eb),
        ]
        for n, ea, eb in pairs
    ]
    header = [
        "task",
        f"facts {a}",
        f"facts {b}",
        f"pages {a}",
        f"pages {b}",
        f"editable {a}",
        f"editable {b}",
        f"numbers not in input {a}",
        f"{b}",
        f"overflow / overlaps {a}",
        f"{b}",
    ]
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

    entries_a, entries_b = [e for _, e, _ in pairs], [e for _, _, e in pairs]
    cost_rows.append(
        [
            "**total**",
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
    args = parser.parse_args(argv)
    table = compare(args.run_a, args.run_b)
    if args.out:
        args.out.write_text(table, encoding="utf-8")
    print(table)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
