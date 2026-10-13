"""An evaluation task: what a user types, the files they give, and what the result must hold."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

KINDS = ("pptx", "xlsx", "docx")
PPTX_TASKS = Path(__file__).resolve().parent / "pptx" / "tasks"
TASK_ROOTS = {kind: Path(__file__).resolve().parent / kind / "tasks" for kind in KINDS}

# Plain-text inputs; the other kinds `input_text` knows are read with their own library.
_TEXT_SUFFIXES = {".md", ".txt", ".csv", ".json"}


@dataclass(frozen=True)
class Expect:
    """`facts`: each entry must appear in the deck; a list inside it holds alternative spellings."""

    facts: list[list[str]]
    pages_min: int
    pages_max: int
    absent: list[str] = field(default_factory=list)
    allowed_numbers: list[str] = field(default_factory=list)
    pictures_min: int = 0
    template: str | None = None  # an input deck whose layouts the result must keep


@dataclass(frozen=True)
class XlsxExpect:
    """What a workbook must hold. A cell address is `Sheet!B2`, a range `Sheet!B2:B13`.

    `cells`: `{"at", "value", "tol"?}`, read after LibreOffice recalculated a copy; a number is
    compared within `tol` (default 0.005), a date as `YYYY-MM-DD`, text exactly.
    `formulas` / `constants`: ranges whose cells must (not) be formulas.
    `number_formats`: `{"at", "any_of"}`, each cell's format must contain one of the strings.
    `bold`: ranges whose cells must be bold.
    `used_range`: per sheet, the range nothing may be written outside of.
    `original` and `untouched`: for an edit, the input workbook and the ranges whose styles must
    be as they were.
    `probe`: `{"set": {address: value}, "expect": [cells]}`, inputs changed on a copy that is
    then recalculated.
    `charts`: `{"kind", "title", "points_min", "axis_titles"}`; `validations`: `{"at", "values"}`.
    """

    facts: list[list[str]]
    absent: list[str] = field(default_factory=list)
    allowed_numbers: list[str] = field(default_factory=list)
    sheets: list[str] = field(default_factory=list)
    cells: list[dict[str, object]] = field(default_factory=list)
    formulas: list[str] = field(default_factory=list)
    constants: list[str] = field(default_factory=list)
    number_formats: list[dict[str, object]] = field(default_factory=list)
    bold: list[str] = field(default_factory=list)
    used_range: dict[str, str] = field(default_factory=dict)
    original: str | None = None
    untouched: list[str] = field(default_factory=list)
    conditional_formats_min: int = 0
    probe: dict[str, object] | None = None
    charts: list[dict[str, object]] = field(default_factory=list)
    validations: list[dict[str, object]] = field(default_factory=list)


@dataclass(frozen=True)
class Task:
    name: str
    directory: Path
    brief: str
    inputs: list[Path]
    expect: Expect | XlsxExpect
    kind: str = "pptx"

    def source_texts(self) -> list[str]:
        """Everything a number in the deck may legitimately come from."""
        return [self.brief, *(t for t in map(input_text, self.inputs) if t)]


def input_text(path: Path) -> str:
    """The text of an input file a person would read; an image or an unknown kind has none."""
    suffix = path.suffix.lower()
    if suffix in _TEXT_SUFFIXES:
        return path.read_text(encoding="utf-8")
    if suffix == ".pptx":
        from .pptx_checks import read_deck

        return read_deck(path).all_text()
    if suffix == ".docx":
        from docx import Document

        document = Document(str(path))
        cells = (c.text for t in document.tables for row in t.rows for c in row.cells)
        return "\n".join([*(p.text for p in document.paragraphs), *cells])
    if suffix in {".xlsx", ".xlsm"}:
        from openpyxl import load_workbook

        workbook = load_workbook(path, data_only=True, read_only=True)
        return "\n".join(
            " ".join("" if v is None else str(v) for v in row)
            for sheet in workbook.worksheets
            for row in sheet.iter_rows(values_only=True)
        )
    if suffix == ".pdf":
        import pdfplumber

        with pdfplumber.open(str(path)) as pdf:
            return "\n".join(page.extract_text() or "" for page in pdf.pages)
    return ""


def _parse_expect(raw: dict[str, object], where: Path) -> Expect:
    pages = raw.get("pages")
    if not (isinstance(pages, list) and len(pages) == 2 and 0 < pages[0] <= pages[1]):
        raise ValueError(f'{where}: "pages" must be [min, max] with 0 < min <= max')
    facts = _facts(raw, where, required=True)
    absent = raw.get("absent", [])
    allowed = raw.get("allowed_numbers", [])
    if not isinstance(absent, list) or not isinstance(allowed, list):
        raise ValueError(f'{where}: "absent" and "allowed_numbers" must be lists')
    return Expect(
        facts=facts,
        pages_min=int(pages[0]),
        pages_max=int(pages[1]),
        absent=[str(a) for a in absent],
        allowed_numbers=[str(a) for a in allowed],
        pictures_min=int(raw.get("pictures_min", 0)),  # type: ignore[call-overload]
        template=str(raw["template"]) if raw.get("template") else None,
    )


def _facts(raw: dict[str, object], where: Path, required: bool) -> list[list[str]]:
    facts_raw = raw.get("facts", [])
    if not isinstance(facts_raw, list) or (required and not facts_raw):
        raise ValueError(f'{where}: "facts" must be a non-empty list')
    facts = [[str(f)] if isinstance(f, str) else [str(a) for a in f] for f in facts_raw]
    if any(not alternatives or not all(alternatives) for alternatives in facts):
        raise ValueError(f"{where}: a fact must be a non-empty string or a list of them")
    return facts


def _list_of(raw: dict[str, object], key: str, kind: type, where: Path) -> list[Any]:
    value = raw.get(key, [])
    if not isinstance(value, list) or not all(isinstance(v, kind) for v in value):
        raise ValueError(f'{where}: "{key}" must be a list of {kind.__name__}')
    return value


def _address_is_valid(address: object) -> bool:
    if not isinstance(address, str):
        return False
    sheet, _, cells = address.rpartition("!")
    return bool(sheet and cells)


def _parse_xlsx_expect(raw: dict[str, object], where: Path) -> XlsxExpect:
    cells = _list_of(raw, "cells", dict, where)
    formulas = _list_of(raw, "formulas", str, where)
    constants = _list_of(raw, "constants", str, where)
    number_formats = _list_of(raw, "number_formats", dict, where)
    charts = _list_of(raw, "charts", dict, where)
    validations = _list_of(raw, "validations", dict, where)
    for spec in (*cells, *number_formats, *validations):
        if not _address_is_valid(spec.get("at")):
            raise ValueError(f'{where}: "at" must look like Sheet!B2 or Sheet!B2:B9: {spec}')
    for spec in cells:
        if "value" not in spec:
            raise ValueError(f'{where}: a cell check needs a "value": {spec}')
        if ":" in spec["at"]:
            raise ValueError(f"{where}: a cell check names one cell, not a range: {spec}")
    for spec in number_formats:
        if not spec.get("any_of") or not isinstance(spec["any_of"], list):
            raise ValueError(f'{where}: a number format check needs "any_of": {spec}')
    bold = _list_of(raw, "bold", str, where)
    for address in (*formulas, *constants, *bold):
        if not _address_is_valid(address):
            raise ValueError(f"{where}: {address!r} must look like Sheet!B2 or Sheet!B2:B9")
    used_range = raw.get("used_range", {})
    if not isinstance(used_range, dict) or not all(
        isinstance(k, str) and isinstance(v, str) for k, v in used_range.items()
    ):
        raise ValueError(f'{where}: "used_range" must map a sheet name to a range')
    probe = raw.get("probe")
    if probe is not None and not (
        isinstance(probe, dict)
        and isinstance(probe.get("set"), dict)
        and isinstance(probe.get("expect"), list)
    ):
        raise ValueError(f'{where}: "probe" needs "set" (address to value) and "expect" (cells)')
    untouched = _list_of(raw, "untouched", str, where)
    original = raw.get("original")
    if (untouched or raw.get("conditional_formats_min")) and not original:
        raise ValueError(f'{where}: "untouched" and "conditional_formats_min" need "original"')
    facts = _facts(raw, where, required=False)
    if not (facts or cells or formulas or probe):
        raise ValueError(f'{where}: expects nothing: give "facts", "cells", "formulas" or "probe"')
    return XlsxExpect(
        facts=facts,
        absent=_list_of(raw, "absent", str, where),
        allowed_numbers=_list_of(raw, "allowed_numbers", str, where),
        sheets=_list_of(raw, "sheets", str, where),
        cells=cells,
        formulas=formulas,
        constants=constants,
        number_formats=number_formats,
        bold=bold,
        used_range=used_range,
        original=str(original) if original else None,
        untouched=untouched,
        conditional_formats_min=int(raw.get("conditional_formats_min", 0)),  # type: ignore[call-overload]
        probe=probe,
        charts=charts,
        validations=validations,
    )


def load_task(directory: Path, kind: str = "pptx") -> Task:
    brief_path = directory / "brief.md"
    expect_path = directory / "expect.json"
    if not brief_path.is_file() or not expect_path.is_file():
        raise ValueError(f"{directory}: needs brief.md and expect.json")
    brief = brief_path.read_text(encoding="utf-8").strip()
    if not brief:
        raise ValueError(f"{brief_path} is empty")
    inputs_dir = directory / "inputs"
    inputs = sorted(p for p in inputs_dir.rglob("*") if p.is_file()) if inputs_dir.is_dir() else []
    raw = json.loads(expect_path.read_text(encoding="utf-8"))
    expect = (
        _parse_xlsx_expect(raw, expect_path) if kind == "xlsx" else _parse_expect(raw, expect_path)
    )
    if getattr(expect, "original", None) and expect.original not in {p.name for p in inputs}:  # type: ignore[union-attr]
        raise ValueError(f"{expect_path}: original {expect.original!r} is not among the inputs")  # type: ignore[union-attr]
    return Task(
        name=directory.name,
        directory=directory,
        brief=brief,
        inputs=inputs,
        expect=expect,
        kind=kind,
    )


def discover(selector: str = "all", root: Path | None = None, kind: str = "pptx") -> list[Task]:
    """`all`, or comma-separated task names or number prefixes (`03`, `03-proposal`)."""
    if kind not in TASK_ROOTS:
        raise ValueError(f"no such kind: {kind}; use one of {', '.join(KINDS)}")
    root = root or TASK_ROOTS[kind]
    directories = sorted(p for p in root.iterdir() if p.is_dir()) if root.is_dir() else []
    if selector != "all":
        wanted = [s.strip() for s in selector.split(",") if s.strip()]
        chosen = [
            d for d in directories if any(d.name == w or d.name.startswith(f"{w}-") for w in wanted)
        ]
        unknown = [
            w
            for w in wanted
            if not any(d.name == w or d.name.startswith(f"{w}-") for d in directories)
        ]
        if unknown:
            raise ValueError(f"no such task: {', '.join(unknown)}")
        directories = chosen
    return [load_task(d, kind) for d in directories]
