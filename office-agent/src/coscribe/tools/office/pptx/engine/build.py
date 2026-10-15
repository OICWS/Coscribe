"""Build a deck from its folder of page sources, check it, and remember what was built.

A deck's sources are a folder of SVG pages, one per slide, in file-name order. Building compiles
them all (it takes well under a second a page), checks the result and writes `build.json` next to
the pages: a hash of each page and of each slide as written. The slide hashes are what makes a
rebuild safe: if the .pptx changed since it was built (edited in PowerPoint, or by an object
tool), rebuilding from the sources would silently throw that work away, so it is refused unless
the caller says to replace it.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pptx import Presentation

from .checker import check_deck, source_text
from .compiler import PageReport, compile_pages

MANIFEST = "build.json"


class DeckChangedError(Exception):
    """The .pptx is not the one these pages last built."""


# Each repair is a model call over every page it touches; past two the cost grows faster than
# the deck improves.
_REPAIR_ROUNDS = 2


@dataclass
class BuildReport:
    path: Path
    pages: list[PageReport]
    # Pages whose source differs from the last build (all of them on a first build).
    changed: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return all(not page.errors for page in self.pages)

    def as_dict(self) -> dict[str, Any]:
        return {
            "path": str(self.path),
            "ok": self.ok,
            "slides": len(self.pages),
            "changed_pages": self.changed,
            "pages": [
                {
                    "page": page.name,
                    "shapes": page.shapes,
                    **({"errors": page.errors} if page.errors else {}),
                    **({"warnings": page.warnings} if page.warnings else {}),
                }
                for page in self.pages
            ],
            **({"warnings": self.warnings} if self.warnings else {}),
        }


def page_files(pages_dir: Path) -> list[Path]:
    """The folder's SVG pages in order: by file name, numbers compared as numbers, so `2.svg`
    comes before `10.svg`."""

    def key(path: Path) -> list[Any]:
        return [
            int(part) if part.isdigit() else part.lower() for part in re.split(r"(\d+)", path.name)
        ]

    return sorted((p for p in pages_dir.glob("*.svg") if p.is_file()), key=key)


def build_deck(
    pages_dir: Path,
    out: Path,
    *,
    sources: Sequence[Path] = (),
    resource_root: Path | None = None,
    replace_changes: bool = False,
    template: Path | None = None,
) -> BuildReport:
    """Compile every page in `pages_dir` into `out`, check it and record the build.

    `sources` are the files the deck's content comes from (for the number check); without any,
    that check is skipped. Raises `DeckChangedError` when `out` exists and is not exactly what
    these pages last built, unless `replace_changes`."""
    files = page_files(pages_dir)
    if not files:
        raise ValueError(f"no .svg pages in {pages_dir}")
    manifest_path = pages_dir / MANIFEST
    previous = _read_manifest(manifest_path)
    if out.exists() and not replace_changes:
        _refuse_if_changed(out, previous)

    texts = [(p.name, p.read_text(encoding="utf-8")) for p in files]
    compiled = compile_pages(
        texts, out, resource_root=resource_root, svg_dir=pages_dir, template=template
    )
    report = BuildReport(out, compiled.pages)
    source_texts, report.warnings = _source_texts(sources)
    check_deck(compiled, source_texts if sources else None)

    before = {entry["page"]: entry["source"] for entry in previous.get("pages", [])}
    hashes = [_sha(text.encode("utf-8")) for _name, text in texts]
    report.changed = [
        name for (name, _), h in zip(texts, hashes, strict=True) if before.get(name) != h
    ]
    failing = previous.get("failing_builds", 0) + 1 if not report.ok else 0
    if failing > _REPAIR_ROUNDS:
        report.warnings.append(
            f"build {failing} in a row with errors: stop repairing. The deck is written; tell the "
            "user which pages still have the problems above, so they can decide"
        )
    manifest = {
        "deck": str(out.resolve()),
        "failing_builds": failing,
        "pages": [
            {"page": name, "source": source, "slide": slide}
            for (name, _), source, slide in zip(texts, hashes, slide_hashes(out), strict=True)
        ],
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def slide_hashes(deck: Path) -> list[str]:
    """One hash per slide over its XML and everything it points to, so a changed picture
    counts as a changed slide too."""
    hashes = []
    for slide in Presentation(str(deck)).slides:
        digest = hashlib.sha256(slide.part.blob)
        for rel in sorted(slide.part.rels.values(), key=lambda r: r.rId):
            digest.update(f"{rel.rId} {rel.reltype} {rel.target_ref}".encode())
            if not rel.is_external:
                digest.update(rel.target_part.blob)
        hashes.append(digest.hexdigest())
    return hashes


def _refuse_if_changed(out: Path, previous: dict[str, Any]) -> None:
    if previous.get("deck") != str(out.resolve()):
        raise DeckChangedError(
            f"{out.name} exists and was not built from these pages; building would replace it"
        )
    recorded = [entry["slide"] for entry in previous["pages"]]
    current = slide_hashes(out)
    if current != recorded:
        changed = [
            str(i)
            for i, (now, then) in enumerate(zip(current, recorded, strict=False), start=1)
            if now != then
        ]
        what = f"slides {', '.join(changed)} differ" if changed else "the slide count differs"
        raise DeckChangedError(
            f"{out.name} changed after it was built ({what}); building from the pages would "
            "throw those changes away"
        )


def _read_manifest(path: Path) -> dict[str, Any]:
    """The last build's record; one that is missing or not in the shape this module writes
    counts as no build, so the deck at its path is treated as not built from these pages."""
    try:
        data: Any = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if not isinstance(data, dict) or not isinstance(data.get("deck"), str):
        return {}
    entries = data.get("pages")
    keys = {"page", "source", "slide"}
    if not isinstance(entries, list) or not all(
        isinstance(e, dict) and keys <= e.keys() for e in entries
    ):
        return {}
    return dict(data)


def _source_texts(sources: Sequence[Path]) -> tuple[list[str], list[str]]:
    texts, problems = [], []
    for path in sources:
        try:
            texts.append(source_text(path))
        except Exception as e:  # one unreadable source must not stop the build
            problems.append(
                f"source {path.name} could not be read ({e}); its numbers are not known"
            )
    return texts, problems


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
