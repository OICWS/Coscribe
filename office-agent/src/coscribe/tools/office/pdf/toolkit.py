from __future__ import annotations

import re
from typing import Any
from xml.sax.saxutils import escape as _xml_escape

from ..._thumbnail import render_thumbnail
from ...files import DEFAULT_IGNORES
from ..markdown_blocks import parse_blocks, parse_inline_runs
from ..table_layout import _CJK_RE, _table_layout
from ..toolkit import WorkspaceToolkit
from .fonts import _pdf_cjk_font
from .text import _pdf_page_texts


class PdfToolkit(WorkspaceToolkit):
    def read_pdf(self, path: str, start_page: int = 1, end_page: int = 0) -> str:
        file_path = self._check_readable(path)
        pages = []
        for index, text in _pdf_page_texts(file_path, start_page, end_page):
            pages.append(f"--- Page {index} ---\n{text.strip()}")
        return "\n\n".join(pages)

    def search_pdf(
        self, query: str, path: str = ".", pattern: str = "*.pdf", regex: bool = False
    ) -> list[dict[str, object]]:
        base = self._scope.resolve(path)
        if not base.exists():
            raise ValueError(f"Path does not exist: {path}")
        if regex:
            try:
                compiled = re.compile(query)
            except re.error as exc:
                raise ValueError(f"Invalid regular expression {query!r}: {exc}") from exc

            def is_match(line: str) -> bool:
                return compiled.search(line) is not None
        else:

            def is_match(line: str) -> bool:
                return query in line

        candidates = [base] if base.is_file() else sorted(base.rglob(pattern))
        matches: list[dict[str, object]] = []
        for item in candidates:
            if not item.is_file():
                continue
            relative_parts = item.relative_to(self._scope.root).parts
            if any(part in DEFAULT_IGNORES for part in relative_parts):
                continue
            for page_number, text in _pdf_page_texts(item):
                for line in text.splitlines():
                    if is_match(line):
                        matches.append(
                            {
                                "path": self._scope.relative(item),
                                "page": page_number,
                                "text": line,
                            }
                        )
                    if len(matches) >= 100:
                        return matches
        return matches

    def write_pdf(self, path: str, content: str, overwrite: bool = True) -> dict[str, object]:
        from reportlab.lib import colors
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.platypus import (
            Paragraph,
            SimpleDocTemplate,
            Spacer,
            Table,
            TableStyle,
        )

        file_path = self._check_writable(path, overwrite)
        styles = getSampleStyleSheet()
        # reportlab's built-in fonts have no Chinese/Japanese/Korean glyphs:
        # such text came out as black boxes with no error.
        cjk_font = _pdf_cjk_font() if _CJK_RE.search(content) else None
        normal = ParagraphStyle(
            "CoscribeNormal", parent=styles["Normal"], fontName=cjk_font or "Helvetica"
        )
        bullet_style = ParagraphStyle("CoscribeBullet", parent=normal, leftIndent=18)
        cell_style = ParagraphStyle("CoscribeCell", parent=normal, fontSize=9, leading=11)

        def rich(text: str) -> str:
            """`text` with its **bold**/*italic* markers as reportlab tags."""
            out = []
            for run_text, bold, italic in parse_inline_runs(text):
                piece = _xml_escape(run_text)
                if bold:
                    piece = f"<b>{piece}</b>"
                if italic:
                    piece = f"<i>{piece}</i>"
                out.append(piece)
            return "".join(out)

        flowables: list[Any] = []
        for block in parse_blocks(content):
            if block.kind == "heading":
                parent = styles[f"Heading{block.level}"]
                heading_style = ParagraphStyle(
                    f"CoscribeHeading{block.level}",
                    parent=parent,
                    fontName=cjk_font or parent.fontName,
                )
                flowables.append(Paragraph(rich(block.text), heading_style))
            elif block.kind == "bullet":
                # Plain ASCII, not "•" -- reportlab's default font maps
                # the unicode bullet glyph in a way pdfplumber/pypdf both
                # mis-render on read-back (a stray "(cid:127)" or a dropped
                # character), confirmed while testing the write/read round trip.
                flowables.append(Paragraph(f"- {rich(block.text)}", bullet_style))
            elif block.kind == "number":
                numbered_text = f"{block.ordinal}. {rich(block.text)}"
                flowables.append(Paragraph(numbered_text, bullet_style))
            elif block.kind == "table" and block.rows:
                # Paragraph cells wrap; a plain string cell runs off the page.
                table = Table(
                    [[Paragraph(rich(str(c)), cell_style) for c in row] for row in block.rows],
                    colWidths=_table_layout(block.rows, 451, [9], padding=12)[1],
                )
                table.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.5, colors.grey)]))
                flowables.append(table)
            else:
                flowables.append(Paragraph(rich(block.text), normal))
            flowables.append(Spacer(1, 6))

        SimpleDocTemplate(str(file_path)).build(flowables)
        preview_path, preview_skipped_reason = render_thumbnail(file_path, self._state_dir)
        return {
            "path": self._scope.relative(file_path),
            "bytes_written": file_path.stat().st_size,
            "preview_path": preview_path,
            "preview_skipped_reason": preview_skipped_reason,
        }
