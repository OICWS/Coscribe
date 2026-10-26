"""The deterministic check of a document written from a spec (decision 0024). It looks at the spec
for what a reader would trip over, then reads the saved document back for what the compiler was
meant to leave in it. No model judges the result: each finding has a code, a place and the change
that clears it, so the author can repair it in one pass."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from .block_images import chart_of
from .block_tables import component_of
from .spec import _FACT, COMPONENTS, Component, Spec

_HEADING = re.compile(r"^(#{1,6})\s+(.*\S)\s*$")
_C = "http://schemas.openxmlformats.org/drawingml/2006/chart"


@dataclass(frozen=True)
class Finding:
    code: str
    where: str
    fix: str

    def as_dict(self) -> dict[str, str]:
        return {"code": self.code, "where": self.where, "fix": self.fix}


def _plain_lines(spec: Spec) -> list[str]:
    return [line for item in spec.items if isinstance(item, str) for line in item.splitlines()]


def _components(spec: Spec) -> list[tuple[int, Component]]:
    """Each component with its number among the components, counted from 1."""
    found = [item for item in spec.items if isinstance(item, Component)]
    return list(enumerate(found, start=1))


def _where(number: int, component: Component) -> str:
    return f"component {number} ({component.name} {component.args}".rstrip() + ")"


def _check_headings(spec: Spec) -> list[Finding]:
    findings: list[Finding] = []
    last = 0
    in_code = False
    for line in _plain_lines(spec):
        if line.lstrip().startswith("```"):
            in_code = not in_code
        match = None if in_code else _HEADING.match(line)
        if match is None:
            continue
        level = len(match.group(1))
        if last and level > last + 1:
            findings.append(
                Finding(
                    "heading-skip",
                    f"heading {match.group(2)!r}",
                    f"Use level {last + 1} here: a heading goes one level below the one before it",
                )
            )
        last = level
    return findings


def _check_facts(content: str, spec: Spec) -> list[Finding]:
    defined = {str(name) for name in _raw_facts(content)}
    used = set(_FACT.findall(content))
    return [
        Finding("unused-fact", f"fact {name!r}", "Use it as {fact:" + name + "} or remove it")
        for name in sorted(defined - used)
    ]


def _raw_facts(content: str) -> dict[Any, Any]:
    from .spec import _split_head

    facts = _split_head(content)[0].get("facts", {})
    return facts if isinstance(facts, dict) else {}


def _check_components(spec: Spec) -> list[Finding]:
    findings: list[Finding] = []
    for number, component in _components(spec):
        where = _where(number, component)
        if component.name == "callout":
            kind, _, rest = component.args.partition(" ")
            if not (component.body or rest).strip():
                findings.append(
                    Finding("empty-callout", where, "Say what the reader must not miss")
                )
        if component.name == "chart":
            title = component.args.partition(" ")[2].strip()
            if not title:
                findings.append(
                    Finding("chart-untitled", where, "Name the chart: `chart bar <title>`")
                )
    return findings


def check_spec(content: str, spec: Spec) -> list[Finding]:
    """What the spec itself gets wrong; nothing here needs the saved file."""
    findings = _check_headings(spec) + _check_facts(content, spec) + _check_components(spec)
    has_title = bool(spec.head.get("title")) or any(
        line.startswith("# ") for line in _plain_lines(spec)
    )
    if not has_title:
        findings.append(Finding("no-title", "document", "Give the document a title in the head"))
    if spec.head.get("toc") and not any(_HEADING.match(line) for line in _plain_lines(spec)):
        findings.append(Finding("empty-contents", "head toc", "Add headings, or drop `toc`"))
    return findings


def _chart_values(xml: str) -> tuple[list[str], list[list[float]]]:
    from lxml import etree

    root = etree.fromstring(xml.encode("utf-8"))
    ns = {"c": _C}
    series = root.findall(".//c:ser", ns)
    categories = [v.text or "" for v in series[0].findall("c:cat//c:v", ns)] if series else []
    values = [[float(v.text or "0") for v in s.findall("c:val//c:v", ns)] for s in series]
    return categories, values


def _chart_matches(component: Component, xml: str) -> bool:
    from ..._chart_data import parse_chart_table

    lines = [line for line in component.body.splitlines() if not line.startswith("caption:")]
    categories, series = parse_chart_table("\n".join(lines), "chart")
    found_categories, found_values = _chart_values(xml)
    return found_categories == categories and found_values == [list(v) for v in series.values()]


def check_document(document: Any, spec: Spec) -> list[Finding]:
    """What the saved document holds against what the spec asked for: every component written once,
    in order, none the compiler does not know, and each chart drawing the numbers of its table."""
    findings: list[Finding] = []
    written: list[tuple[str, Any]] = []
    for element in document.element.body:
        name = component_of(element)
        if name is not None:
            written.append((name.split("_", 1)[0], element))
    for name, _ in written:
        if name not in (*COMPONENTS, "cover"):
            findings.append(
                Finding(
                    "unknown-component", f"component {name!r}", "Rewrite it with a known component"
                )
            )
    # A page break has no bookmark: only the components that leave one can be counted.
    asked = [(n, c) for n, c in _components(spec) if c.name != "pagebreak"]
    # The cover comes from the head, not from a component, and leads the body.
    cover = ["cover"] if spec.head.get("cover", "none") != "none" else []
    if [name for name, _ in written] != [*cover, *(c.name for _, c in asked)]:
        findings.append(
            Finding(
                "components-lost",
                "document",
                "The saved document does not hold the components in the spec, in the same order",
            )
        )
        return findings
    for (number, component), (_, element) in zip(asked, written[len(cover) :], strict=True):
        if component.name != "chart":
            continue
        drawn = chart_of(element, document)
        if drawn is None or not _chart_matches(component, drawn["xml"]):
            findings.append(
                Finding(
                    "chart-data",
                    _where(number, component),
                    "The chart does not draw the numbers of its table: write the table again",
                )
            )
    return findings
