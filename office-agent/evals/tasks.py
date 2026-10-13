"""An evaluation task: what a user types, the files they give, and what the result must hold."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

PPTX_TASKS = Path(__file__).resolve().parent / "pptx" / "tasks"

# Text a check can read without a converter; other inputs (images, templates, decks) are
# copied into the workspace and mentioned by the brief.
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
class Task:
    name: str
    directory: Path
    brief: str
    inputs: list[Path]
    expect: Expect

    def source_texts(self) -> list[str]:
        """Everything a number in the deck may legitimately come from."""
        texts = [self.brief]
        for path in self.inputs:
            if path.suffix.lower() in _TEXT_SUFFIXES:
                texts.append(path.read_text(encoding="utf-8"))
            elif path.suffix.lower() == ".pptx":
                from .pptx_checks import read_deck

                texts.append(read_deck(path).all_text())
        return texts


def _parse_expect(raw: dict[str, object], where: Path) -> Expect:
    facts_raw = raw.get("facts")
    pages = raw.get("pages")
    if not isinstance(facts_raw, list) or not facts_raw:
        raise ValueError(f'{where}: "facts" must be a non-empty list')
    if not (isinstance(pages, list) and len(pages) == 2 and 0 < pages[0] <= pages[1]):
        raise ValueError(f'{where}: "pages" must be [min, max] with 0 < min <= max')
    facts = [[str(f)] if isinstance(f, str) else [str(a) for a in f] for f in facts_raw]
    if any(not alternatives or not all(alternatives) for alternatives in facts):
        raise ValueError(f"{where}: a fact must be a non-empty string or a list of them")
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


def load_task(directory: Path) -> Task:
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
    return Task(
        name=directory.name,
        directory=directory,
        brief=brief,
        inputs=inputs,
        expect=_parse_expect(raw, expect_path),
    )


def discover(selector: str = "all", root: Path = PPTX_TASKS) -> list[Task]:
    """`all`, or comma-separated task names or number prefixes (`03`, `03-proposal`)."""
    directories = sorted(p for p in root.iterdir() if p.is_dir())
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
    return [load_task(d) for d in directories]
