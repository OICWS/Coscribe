"""Golden (characterization) tests of the XML the docx tools write.

`tools/documents.py` is to be split into `tools/office/docx/` and `tools/office/pdf/` by pure
moves. A pure move must leave every file the tools write unchanged, and these tests are how that
is shown: each document is built through the public tools, reduced to canonical text
(`tests/docx_canonical.py`), and compared with a checked-in golden under `tests/golden/docx/`.
A change that alters what a document contains edits its golden in the same pull request.
`UPDATE_GOLDENS=1 pytest tests/test_docx_golden.py` rewrites them; read the diff before
committing it.
"""

from __future__ import annotations

import contextlib
import difflib
import os
import re
import shutil
from collections.abc import Callable
from pathlib import Path

import pytest

from coscribe.tools.documents import build_document_tools

from .docx_canonical import canonical_parts

GOLDEN_DIR = Path(__file__).parent / "golden" / "docx"

Tools = dict[str, Callable[..., object]]


def _tools(root: Path) -> Tools:
    return {tool.__name__: tool for tool in build_document_tools(root)}  # type: ignore[attr-defined]


def _headings_and_runs(tools: Tools) -> None:
    tools["write_docx"](
        path="doc.docx",
        content="# Quarterly review\n\nRevenue grew **12%** and costs were *flat*.\n\n"
        "## Outlook\n\n### Risks\n\nPlain paragraph with ***both*** styles.",
    )


def _lists(tools: Tools) -> None:
    tools["write_docx"](
        path="doc.docx",
        content="# Plan\n\n- first point\n- second point\n\n"
        "1. step one\n2. step two\n3. step three",
    )


def _table(tools: Tools) -> None:
    tools["write_docx"](
        path="doc.docx",
        content="# Results\n\n| Region | Revenue | Share |\n| --- | --- | --- |\n"
        "| North | 1200 | 60% |\n| South | 22.5 | 40% |",
    )


def _toc(tools: Tools) -> None:
    tools["write_docx"](
        path="doc.docx",
        content="# Handbook\n\n[TOC]\n\n## Setup\n\nInstall it.\n\n## Usage\n\nRun it.",
    )


def _landscape(tools: Tools) -> None:
    tools["write_docx"](
        path="doc.docx",
        content="# Wide sheet\n\nLaid out on A4 landscape.",
        page_size="a4",
        orientation="landscape",
    )


def _cjk(tools: Tools) -> None:
    tools["write_docx"](
        path="doc.docx",
        content="# 季度报告\n\n收入增长 **12%**，成本*持平*。\n\n- 新增两个市场\n\n"
        "| 地区 | 收入 |\n| --- | --- |\n| 华北 | 1200 |",
    )


def _base(tools: Tools) -> None:
    _headings_and_runs(tools)


def _tracked_insert(tools: Tools) -> None:
    _base(tools)
    tools["insert_docx_text"](
        path="doc.docx", text=" sharply", context_before="Revenue grew", author="Reviewer"
    )


def _tracked_delete(tools: Tools) -> None:
    # The deleted text spans a bold run and an italic run.
    _base(tools)
    tools["delete_docx_text"](path="doc.docx", text="12% and costs", author="Reviewer")


def _tracked_replace(tools: Tools) -> None:
    _base(tools)
    tools["replace_docx_text"](
        path="doc.docx", find="Plain paragraph", replace="Short paragraph", author="Reviewer"
    )


def _three_tracked_edits(tools: Tools) -> None:
    _base(tools)
    tools["insert_docx_text"](
        path="doc.docx", text=" sharply", context_before="Revenue grew", author="Reviewer"
    )
    tools["delete_docx_text"](path="doc.docx", text=" and costs were flat", author="Reviewer")
    tools["replace_docx_text"](
        path="doc.docx", find="Plain paragraph", replace="Short paragraph", author="Reviewer"
    )


def _accepted_changes(tools: Tools) -> None:
    _three_tracked_edits(tools)
    tools["accept_docx_tracked_changes"](path="doc.docx")


def _rejected_changes(tools: Tools) -> None:
    _three_tracked_edits(tools)
    tools["reject_docx_tracked_changes"](path="doc.docx")


def _image(tools: Tools) -> None:
    _base(tools)
    # Copied, not drawn at test time: a PNG's bytes depend on the encoder and zlib in use.
    shutil.copyfile(GOLDEN_DIR / "assets" / "logo.png", "logo.png")
    tools["add_docx_image"](
        path="doc.docx", image_path="logo.png", after_text="Outlook", caption="Our logo", width=1.5
    )


def _chart(tools: Tools) -> None:
    _base(tools)
    tools["add_docx_chart"](
        path="doc.docx",
        chart_type="bar",
        data="| Quarter | Revenue |\n| --- | --- |\n| Q1 | 100 |\n| Q2 | 120 |\n| Q3 | 90 |",
        title="Results",
        after_text="Outlook",
        caption="Revenue by quarter",
    )


DOCUMENTS: dict[str, Callable[[Tools], None]] = {
    "accepted_changes": _accepted_changes,
    "chart": _chart,
    "cjk": _cjk,
    "headings_and_runs": _headings_and_runs,
    "image": _image,
    "landscape": _landscape,
    "lists": _lists,
    "rejected_changes": _rejected_changes,
    "table": _table,
    "toc": _toc,
    "tracked_delete": _tracked_delete,
    "tracked_insert": _tracked_insert,
    "tracked_replace": _tracked_replace,
}


def build_document(name: str, root: Path) -> Path:
    """Build document `name` in `root` and return its path."""
    root.mkdir(parents=True, exist_ok=True)
    with contextlib.chdir(root):
        DOCUMENTS[name](_tools(root))
    return root / "doc.docx"


@pytest.fixture(autouse=True)
def _no_libreoffice(monkeypatch: pytest.MonkeyPatch) -> None:
    # The preview render only reads the file; skipping it keeps these tests fast and the same on
    # machines with and without LibreOffice.
    monkeypatch.setattr("shutil.which", lambda name: None)


# Styles, theme, settings and the package boilerplate come from python-docx's template and are
# the same in every document; stored once they would be most of every golden. A document whose
# copy differs still shows its own full text.
SHARED_GOLDEN = GOLDEN_DIR / "_shared.txt"
_SHARED_PREFIXES = (
    "_rels/.rels",
    "customXml/",
    "docProps/app.xml",
    "docProps/thumbnail.jpeg",
    "word/styles.xml",
    "word/stylesWithEffects.xml",
    "word/theme/",
    "word/settings.xml",
    "word/fontTable.xml",
    "word/webSettings.xml",
    "word/numbering.xml",
)
_SHARED_SOURCE_DOCUMENT = "headings_and_runs"


def _shared_parts(parts: dict[str, str]) -> dict[str, str]:
    return {name: text for name, text in parts.items() if name.startswith(_SHARED_PREFIXES)}


def _render(parts: dict[str, str]) -> str:
    return "".join(f"===== {name}\n{text}" for name, text in parts.items())


def _parse(text: str) -> dict[str, str]:
    parts: dict[str, str] = {}
    for chunk in re.split(r"^===== ", text, flags=re.MULTILINE)[1:]:
        name, _, body = chunk.partition("\n")
        parts[name] = body
    return parts


def _document_golden_text(parts: dict[str, str], shared: dict[str, str]) -> str:
    return _render(
        {
            name: "<same as _shared.txt>\n" if shared.get(name) == text else text
            for name, text in parts.items()
        }
    )


def _expected_and_diff(golden: Path, actual: str) -> tuple[str, str]:
    if os.environ.get("UPDATE_GOLDENS") == "1":
        golden.parent.mkdir(parents=True, exist_ok=True)
        golden.write_text(actual, encoding="utf-8", newline="\n")
    expected = golden.read_text(encoding="utf-8")
    diff = "".join(
        difflib.unified_diff(
            expected.splitlines(keepends=True),
            actual.splitlines(keepends=True),
            f"golden/docx/{golden.name}",
            "built now",
            n=2,
        )
    )
    return expected, (
        f"{golden.name} differs from what the tools build; if the change is intended, run "
        f"UPDATE_GOLDENS=1 pytest tests/test_docx_golden.py and commit the diff:\n{diff[:4000]}"
    )


def _built_shared(tmp_path: Path) -> dict[str, str]:
    path = build_document(_SHARED_SOURCE_DOCUMENT, tmp_path / "_shared")
    return _shared_parts(canonical_parts(path))


def test_shared_golden_matches_the_plain_document(tmp_path: Path) -> None:
    actual = _render(_built_shared(tmp_path))
    expected, message = _expected_and_diff(SHARED_GOLDEN, actual)
    assert actual == expected, message


@pytest.mark.parametrize("name", sorted(DOCUMENTS))
def test_document_matches_its_golden(name: str, tmp_path: Path) -> None:
    parts = canonical_parts(build_document(name, tmp_path / name))
    # When regenerating, the shared golden may not be written yet (test order is not fixed).
    shared = (
        _built_shared(tmp_path)
        if os.environ.get("UPDATE_GOLDENS") == "1"
        else _parse(SHARED_GOLDEN.read_text(encoding="utf-8"))
    )
    actual = _document_golden_text(parts, shared)
    expected, message = _expected_and_diff(GOLDEN_DIR / f"{name}.txt", actual)
    assert actual == expected, message


def test_the_shared_golden_round_trips_through_the_parser() -> None:
    text = SHARED_GOLDEN.read_text(encoding="utf-8")
    assert _render(_parse(text)) == text


def test_every_golden_belongs_to_a_document() -> None:
    stale = sorted(
        path.stem
        for path in GOLDEN_DIR.glob("*.txt")
        if path.stem not in DOCUMENTS and path != SHARED_GOLDEN
    )
    assert stale == [], f"goldens with no document that builds them: {stale}"
