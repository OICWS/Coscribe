"""A generated Word file's pages as the office program laid them out (decision 0026): empty pages,
text past the paper's edge and a last page of a line or two are named; a document that looks right
is not; a check that could not run says so rather than passing."""

from __future__ import annotations

from pathlib import Path

import pytest

from coscribe.tools._page_check import checked_pages, page_problems


def _pdf(path: Path, pages: list[list[tuple[float, float, str]]]) -> Path:
    """A PDF of A4 pages, each `(x, y, text)` drawn in Helvetica 11 pt; an empty list is a blank
    page."""
    objects = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        "",
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    kids = []
    for lines in pages:
        stream = "".join(f"BT /F1 11 Tf {x} {y} Td ({text}) Tj ET\n" for x, y, text in lines)
        objects.append(f"<< /Length {len(stream)} >>\nstream\n{stream}endstream")
        content = len(objects)
        objects.append(
            "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
            f"/Resources << /Font << /F1 3 0 R >> >> /Contents {content} 0 R >>"
        )
        kids.append(f"{len(objects)} 0 R")
    objects[1] = f"<< /Type /Pages /Kids [{' '.join(kids)}] /Count {len(kids)} >>"
    out, offsets = "%PDF-1.4\n", []
    for number, body in enumerate(objects, 1):
        offsets.append(len(out))
        out += f"{number} 0 obj\n{body}\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n"
    out += "".join(f"{offset:010d} 00000 n \n" for offset in offsets)
    out += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n"
    path.write_bytes(out.encode("latin-1"))
    return path


_FULL = [
    (72, 800 - 14 * n, "A full line of the report that fills the page with words")
    for n in range(40)
]


def test_a_document_whose_pages_look_right_has_no_problems(tmp_path: Path) -> None:
    pdf = _pdf(tmp_path / "ok.pdf", [_FULL, _FULL[:20]])

    assert page_problems(pdf) == {"pages": 2, "problems": []}


def test_an_empty_page_text_past_the_edge_and_a_spilled_last_line_are_named(
    tmp_path: Path,
) -> None:
    wide = [*_FULL[:10], (520, 500, "a table column that runs off the paper")]
    pdf = _pdf(tmp_path / "bad.pdf", [_FULL, [], wide, [(72, 800, "Thanks.")]])

    problems = page_problems(pdf)["problems"]

    assert problems == [
        "empty page: 2",
        "text runs past the paper's edge (a table or line too wide): page 3",
        "page 4, the last, holds only a line or two: fit it on the page before",
    ]


def test_a_check_that_could_not_run_is_not_a_pass() -> None:
    assert checked_pages({}) == "not checked (needs Microsoft Office, WPS Office or LibreOffice)"
    assert checked_pages({"pages": 1, "problems": []})["problems"] == []


def test_write_docx_returns_what_the_office_program_laid_out(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from coscribe.tools import _office_com
    from coscribe.tools.office.document_tools import build_document_tools

    def word(source: Path, target: Path, to_format: str, timeout: float) -> str:
        _pdf(target, [_FULL, []])
        return "Microsoft Word"

    monkeypatch.setattr(_office_com, "convert", word)
    tools = {t.__name__: t for t in build_document_tools(tmp_path, state_dir=tmp_path / "state")}

    result = tools["write_docx"](path="report.docx", content="# Report\n\nText.")

    assert result["page_check"] == {
        "laid_out_by": "Microsoft Word",
        "pages": 2,
        "problems": ["empty page: 2"],
    }
