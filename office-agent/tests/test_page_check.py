"""A generated Word file's pages as the office program laid them out (decision 0026): empty pages,
text past the paper's edge and a last page of a line or two are named; a document that looks right
is not; a check that could not run says so rather than passing."""

from __future__ import annotations

from pathlib import Path

import pytest

from coscribe.tools._page_check import checked_pages, page_problems


def _pdf(path: Path, pages: list[list[tuple[float, float, str]]], rotate: int = 0) -> Path:
    """A PDF of A4 pages, each `(x, y, text)` drawn in Helvetica 11 pt; an empty list is a blank
    page. `rotate` turns every page, its MediaBox still portrait, as an exporter writes a landscape
    section."""
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
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Rotate {rotate} "
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
    (72, 730 - 14 * n, "A full line of the report that fills the page with words")
    for n in range(48)
]
_HALF = _FULL[:20]


def test_a_document_whose_pages_look_right_has_no_problems(tmp_path: Path) -> None:
    pdf = _pdf(tmp_path / "ok.pdf", [_FULL, _HALF])

    assert page_problems(pdf) == {"pages": 2, "problems": []}


def test_an_empty_page_text_past_the_edge_and_a_spilled_last_line_are_named(
    tmp_path: Path,
) -> None:
    wide = [*_FULL[:10], (520, 500, "a table column that runs off the paper")]
    pdf = _pdf(tmp_path / "bad.pdf", [_FULL, [], wide, _FULL, [(72, 730, "Thanks.")]])

    problems = page_problems(pdf)["problems"]

    assert problems == [
        "empty page: 2",
        "text runs past the paper's edge (a table or line too wide): page 3",
        "page 5, the last, holds only a line or two: fit it on the page before",
    ]


def test_a_header_footer_and_page_number_on_every_page_are_not_body(tmp_path: Path) -> None:
    def framed(n: int, body: list[tuple[float, float, str]]) -> list[tuple[float, float, str]]:
        header = (72, 815, "ACME Ltd, 1 Long Street, Springfield, a letterhead address line")
        return [header, *body, (270, 20, f"Page {n} of 4")]

    pdf = _pdf(
        tmp_path / "framed.pdf",
        [framed(1, _FULL), framed(2, []), framed(3, _FULL), framed(4, [(72, 730, "Thanks.")])],
    )

    assert page_problems(pdf)["problems"] == [
        "empty page: 2",
        "page 4, the last, holds only a line or two: fit it on the page before",
    ]


def test_a_short_last_page_after_a_half_empty_one_was_meant(tmp_path: Path) -> None:
    pdf = _pdf(tmp_path / "letter.pdf", [_HALF, [(72, 730, "Sincerely, Name")]])

    assert page_problems(pdf)["problems"] == []


def test_a_rotated_page_measures_its_text_against_its_own_paper(tmp_path: Path) -> None:
    pdf = _pdf(tmp_path / "landscape.pdf", [_FULL], rotate=90)

    assert page_problems(pdf)["problems"] == []


def test_a_check_that_could_not_run_is_not_a_pass_and_says_why() -> None:
    assert checked_pages({}, "no office program was found") == (
        "not checked (no office program was found)"
    )
    failed = {"failed": "Microsoft Word laid it out, but its PDF could not be read"}
    assert checked_pages(failed, None) == (
        "not checked (Microsoft Word laid it out, but its PDF could not be read)"
    )
    assert checked_pages({"pages": 1, "problems": []}, None)["problems"] == []


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


def test_a_pdf_the_check_cannot_read_still_gets_a_preview_and_says_so(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from coscribe.tools import _office_com, _thumbnail
    from coscribe.tools.office.document_tools import build_document_tools

    def word(source: Path, target: Path, to_format: str, timeout: float) -> str:
        _pdf(target, [_FULL])
        return "Microsoft Word"

    def unreadable(pdf_path: Path) -> dict[str, object]:
        raise RuntimeError("PDFium could not load the document")

    monkeypatch.setattr(_office_com, "convert", word)
    monkeypatch.setattr(_thumbnail, "page_problems", unreadable)
    tools = {t.__name__: t for t in build_document_tools(tmp_path, state_dir=tmp_path / "state")}
    tools["write_docx"](path="report.docx", content="# Report\n\nText.")

    result = tools["accept_docx_tracked_changes"](path="report.docx")

    assert result["preview_path"]
    assert result["page_check"] == (
        "not checked (Microsoft Word laid it out, but its PDF could not be read)"
    )
