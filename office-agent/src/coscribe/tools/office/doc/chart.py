"""A chart block of a Doc: a fenced block `chart`, whose first line names the kind (`bar`, `line` or
`pie`, then an optional title) and whose other lines are the data as a pipe table."""

from __future__ import annotations

from dataclasses import dataclass

from ..._chart_data import CHART_TYPES, parse_chart_table


@dataclass(frozen=True)
class Chart:
    kind: str
    title: str
    categories: list[str]
    series: dict[str, list[float]]


def parse_chart(block_text: str) -> Chart:
    """The chart a block holds; `ValueError`, with text that is safe to show, when it is not one."""
    lines = block_text.strip().splitlines()
    if len(lines) < 2 or not lines[0].lstrip().startswith(("```", "~~~")):
        raise ValueError("A chart is a fenced block that opens with ```chart")
    body = lines[1:-1] if lines[-1].strip().startswith(("```", "~~~")) else lines[1:]
    first, _, data = "\n".join(body).strip().partition("\n")
    kind, _, title = first.strip().partition(" ")
    if kind.lower() not in CHART_TYPES:
        raise ValueError(f"A chart is {', '.join(sorted(CHART_TYPES))}: the first line names one")
    categories, series = parse_chart_table(data, "chart")
    if kind.lower() == "pie" and len(series) > 1:
        raise ValueError("A pie chart has one data column besides the category column")
    return Chart(kind.lower(), title.strip(), categories, series)
