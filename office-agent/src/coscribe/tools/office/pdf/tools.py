from __future__ import annotations

from collections.abc import Callable
from typing import Any

from ....runtime import tool_metadata
from ..._output_truncation import cap_read_output
from .toolkit import PdfToolkit


def build_pdf_tools(toolkit: PdfToolkit) -> list[Callable[..., Any]]:
    """The PDF tools, bound to `toolkit`."""

    def read_pdf(path: str, start_page: int = 1, end_page: int = 0) -> str:
        """Extract the text contents of a PDF file under the workspace, page by page.

        For a long PDF, find the relevant pages with `search_pdf` first and
        read only that range, rather than the whole document.

        Args:
            path: file to read, relative to the workspace root
            start_page: first page to read (1-based)
            end_page: last page to read, inclusive; 0 means through the last page
        """
        return cap_read_output(
            toolkit.read_pdf(path=path, start_page=start_page, end_page=end_page),
            "read fewer pages at a time with start_page and end_page, or use search_pdf",
        )

    def write_pdf(path: str, content: str, overwrite: bool = True) -> dict[str, object]:
        """Create a PDF file under the workspace from structured text.

        Uses the same markdown subset as `write_docx` (headings, bullets,
        numbered items, pipe tables, and plain paragraphs).

        The response's `preview_path` (when the file can be drawn) names
        a rendered thumbnail of the first page the user can see in the
        chat UI -- not something to fetch or parse yourself.

        Args:
            path: file to write, relative to the workspace root
            content: document content in the markdown subset described above
            overwrite: whether to replace the file if it already exists
        """
        return toolkit.write_pdf(path=path, content=content, overwrite=overwrite)

    def search_pdf(
        query: str, path: str = ".", pattern: str = "*.pdf", regex: bool = False
    ) -> list[dict[str, object]]:
        """Search PDF files under the workspace line by line, returning each
        matching line with its page number (at most 100 matches).

        Finds matches without needing to read_pdf an entire (possibly large)
        document into context first.

        Args:
            query: substring to search for, or a Python regular expression when regex is true
            path: a PDF file, or a directory to search under, relative to the workspace root
            pattern: glob pattern to filter PDF files by when path is a directory
            regex: treat query as a regular expression instead of a literal substring
        """
        return toolkit.search_pdf(query=query, path=path, pattern=pattern, regex=regex)

    return [
        tool_metadata(read_pdf, risk_category="READ", category="documents"),
        tool_metadata(write_pdf, risk_category="WRITE_LOCAL", category="documents"),
        tool_metadata(search_pdf, risk_category="READ", category="documents"),
    ]
