from __future__ import annotations

from pathlib import Path
from typing import Any

from ..._file_locks import locked_by_path
from ..._ooxml_validate import assert_wml_valid
from ..._thumbnail import render_thumbnail
from ..markdown_blocks import parse_blocks
from ..toolkit import WorkspaceToolkit
from ._xml import (
    _add_inline_runs,
    _add_toc,
    _apply_page_setup,
    _build_comments_xml,
    _ChangeIdCounter,
    _clear_body,
    _enable_update_fields,
    _fill_docx_table,
    _fill_toc,
    _locate_paragraph,
    _mark_body_deleted,
    _mark_paragraph_inserted,
    _new_comment_anchor,
    _text_column_emu,
    _TrackedDocxHost,
    _write_comments_part,
)


def _finish_tocs(
    document: Any,
    toc_paragraphs: list[Any],
    headings: list[tuple[int, str]],
    change_author: str | None,
    change_ids: _ChangeIdCounter,
) -> bool:
    for toc_paragraph in toc_paragraphs:
        added = _fill_toc(document, toc_paragraph, headings)
        if change_author is not None:
            for entry in [toc_paragraph, *added]:
                _mark_paragraph_inserted(entry._p, change_author, change_ids)
    if toc_paragraphs:
        _enable_update_fields(document)
    return bool(toc_paragraphs)


class DocxToolkit(WorkspaceToolkit):
    @locked_by_path
    def read_docx(self, path: str) -> str:
        import mammoth
        from markdownify import markdownify

        file_path = self._check_readable(path)
        with file_path.open("rb") as docx_file:
            html = mammoth.convert_to_html(docx_file).value
        return markdownify(html, heading_style="ATX", bullets="-", table_infer_header=True).strip()

    @locked_by_path
    def write_docx(
        self,
        path: str,
        content: str,
        overwrite: bool = True,
        template_path: str = "",
        page_size: str = "",
        orientation: str = "",
        track_changes: bool = False,
        change_author: str = "Coscribe",
        comment_author: str = "Coscribe",
    ) -> dict[str, object]:
        from docx import Document

        file_path = self._check_writable(path, overwrite)
        change_ids = _ChangeIdCounter()
        if template_path:
            template_file = self._check_readable(template_path)
            document = Document(str(template_file))
            if track_changes:
                _mark_body_deleted(document, change_author, change_ids)
            else:
                _clear_body(document)
        else:
            document = Document()

        if page_size or orientation:
            _apply_page_setup(document, page_size, orientation)
        toc_paragraphs: list[Any] = []
        headings: list[tuple[int, str]] = []
        pending_comments: list[tuple[Any, str]] = []
        previous_kind = ""
        for block in parse_blocks(content):
            paragraph = None
            if block.kind == "heading":
                paragraph = document.add_heading("", level=block.level)
                _add_inline_runs(paragraph, block.text)
                headings.append((block.level, paragraph.text))
            elif block.kind == "bullet":
                paragraph = document.add_paragraph(style="List Bullet")
                _add_inline_runs(paragraph, block.text)
            elif block.kind == "number":
                paragraph = document.add_paragraph(style="List Number")
                _add_inline_runs(paragraph, block.text)
            elif block.kind == "toc":
                toc_paragraphs.append(_add_toc(document))
            elif block.kind == "table" and block.rows:
                if previous_kind == "table":
                    # Word joins back-to-back tables into one.
                    spacer = document.add_paragraph()
                    if track_changes:
                        _mark_paragraph_inserted(spacer._p, change_author, change_ids)
                _fill_docx_table(document, block)
            else:
                paragraph = document.add_paragraph()
                _add_inline_runs(paragraph, block.text)

            previous_kind = block.kind
            if paragraph is None:
                continue
            if track_changes:
                _mark_paragraph_inserted(paragraph._p, change_author, change_ids)
            if block.comment:
                pending_comments.append((paragraph._p, block.comment))

        # Written only now, so the TOC also lists the headings after its marker.
        has_toc = _finish_tocs(
            document, toc_paragraphs, headings, change_author if track_changes else None, change_ids
        )
        for index, (paragraph_element, _) in enumerate(pending_comments):
            _new_comment_anchor(paragraph_element, str(index))

        assert_wml_valid(document.element, "write_docx")
        document.save(str(file_path))

        if pending_comments:
            comments_xml = _build_comments_xml(
                [
                    (str(index), comment_author, text)
                    for index, (_, text) in enumerate(pending_comments)
                ]
            )
            _write_comments_part(file_path, comments_xml)

        preview_path, preview_skipped_reason = render_thumbnail(file_path, self._state_dir)
        return {
            "path": self._scope.relative(file_path),
            "bytes_written": file_path.stat().st_size,
            "preview_path": preview_path,
            "preview_skipped_reason": preview_skipped_reason,
            "has_toc": has_toc,
            "comments_added": len(pending_comments),
            "tracked_changes": track_changes,
        }

    def _open_for_tracked_edit(self, path: str) -> tuple[Path, Any, _TrackedDocxHost]:
        from docx import Document

        file_path = self._check_editable(path)
        document = Document(str(file_path))
        return file_path, document, _TrackedDocxHost(document)

    def _save_tracked_edit(self, file_path: Path, document: Any) -> dict[str, object]:
        assert_wml_valid(document.element, "tracked_docx_edit")
        document.save(str(file_path))
        preview_path, preview_skipped_reason = render_thumbnail(file_path, self._state_dir)
        return {
            "path": self._scope.relative(file_path),
            "bytes_written": file_path.stat().st_size,
            "preview_path": preview_path,
            "preview_skipped_reason": preview_skipped_reason,
        }

    @locked_by_path
    def add_docx_chart(
        self,
        path: str,
        chart_type: str,
        data: str,
        title: str = "",
        after_text: str = "",
        caption: str = "",
        width: float = 0.0,
        height: float = 3.2,
    ) -> dict[str, object]:
        from docx import Document
        from docx.shared import Emu, Inches

        from ..._chart_data import CHART_TYPES, parse_chart_table
        from ..._docx_chart import add_chart_paragraph

        if chart_type not in CHART_TYPES:
            raise ValueError(
                f"Unknown chart_type {chart_type!r}. Use one of: {', '.join(sorted(CHART_TYPES))}"
            )
        categories, series = parse_chart_table(data, "add_docx_chart")
        if chart_type == "pie" and len(series) > 1:
            raise ValueError("pie charts take exactly one data column plus the category column")

        file_path = self._check_editable(path)
        document = Document(str(file_path))
        # Never wider than the text column: a chart sized for a slide runs
        # off the page edge in a portrait document.
        column = _text_column_emu(document)
        width_emu = min(int(Inches(width)), column) if width > 0 else column
        paragraph = add_chart_paragraph(
            document,
            chart_type,
            categories,
            series,
            title,
            width_emu,
            int(Emu(int(Inches(height)))),
        )
        self._place_after(document, paragraph, after_text, caption)
        return self._save_tracked_edit(file_path, document)

    @locked_by_path
    def add_docx_image(
        self,
        path: str,
        image_path: str,
        after_text: str = "",
        caption: str = "",
        width: float = 0.0,
    ) -> dict[str, object]:
        from docx import Document
        from docx.shared import Emu, Inches

        image_file = self._check_readable(image_path)
        file_path = self._check_editable(path)
        document = Document(str(file_path))
        column = _text_column_emu(document)
        paragraph = document.add_paragraph()
        run = paragraph.add_run()
        try:
            picture = run.add_picture(str(image_file))
        except Exception as error:  # python-docx raises UnrecognizedImageError
            raise ValueError(f"{image_path} is not a PNG, JPEG, GIF or BMP image") from error
        target = min(int(Inches(width)), column) if width > 0 else min(picture.width, column)
        picture.height = Emu(int(picture.height * target / picture.width))
        picture.width = Emu(target)
        self._place_after(document, paragraph, after_text, caption)
        return self._save_tracked_edit(file_path, document)

    @staticmethod
    def _place_after(document: Any, paragraph: Any, after_text: str, caption: str) -> None:
        """Centre `paragraph`, add its caption, and move both after the
        paragraph named by `after_text` (default: leave at the end)."""
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        from docx.text.paragraph import Paragraph

        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        last = paragraph
        if caption:
            caption_paragraph = document.add_paragraph()
            run = caption_paragraph.add_run(caption)
            run.italic = True
            caption_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            last = caption_paragraph
        if not after_text:
            return
        # The new paragraphs are still the last two in the body; find the
        # anchor among the others.
        moving = {id(paragraph._p), id(last._p)}  # noqa: SLF001
        others = [p for p in document.paragraphs if id(p._p) not in moving]  # noqa: SLF001
        wanted = after_text.strip()
        exact = [p for p in others if p.text.strip() == wanted]
        matches = exact or [p for p in others if wanted in p.text]
        if not matches:
            raise ValueError(f"No paragraph contains {after_text!r}; the chart was not added.")
        if len(matches) > 1:
            raise ValueError(
                f"{len(matches)} paragraphs contain {after_text!r}; give more of the "
                "text so it names one."
            )
        anchor: Any = matches[0]._p  # noqa: SLF001
        anchor.addnext(paragraph._p)  # noqa: SLF001
        if last is not paragraph:
            paragraph._p.addnext(last._p)  # noqa: SLF001
        del Paragraph

    @locked_by_path
    def insert_docx_text(
        self,
        path: str,
        text: str,
        context_before: str,
        context_after: str = "",
        track_changes: bool = True,
        author: str = "Coscribe",
        ignore_case: bool = False,
    ) -> dict[str, object]:
        if not context_before:
            raise ValueError(
                "context_before is required -- it names the existing text to "
                "insert after; context_after alone cannot locate an insertion point"
            )
        file_path, document, host = self._open_for_tracked_edit(path)
        para_id = _locate_paragraph(
            host._document_element, context_before, "", context_after, ignore_case=ignore_case
        )
        result = host.insert_text(
            para_id,
            text,
            author=author,
            context_before=context_before,
            context_after=context_after,
            ignore_case=ignore_case,
            tracked=track_changes,
        )
        result.update(self._save_tracked_edit(file_path, document))
        return result

    @locked_by_path
    def delete_docx_text(
        self,
        path: str,
        text: str,
        context_before: str = "",
        context_after: str = "",
        track_changes: bool = True,
        author: str = "Coscribe",
        ignore_case: bool = False,
    ) -> dict[str, object]:
        file_path, document, host = self._open_for_tracked_edit(path)
        para_id = _locate_paragraph(
            host._document_element, text, context_before, context_after, ignore_case=ignore_case
        )
        result = host.delete_text(
            para_id,
            text,
            author=author,
            context_before=context_before,
            context_after=context_after,
            ignore_case=ignore_case,
            tracked=track_changes,
        )
        result.update(self._save_tracked_edit(file_path, document))
        return result

    @locked_by_path
    def replace_docx_text(
        self,
        path: str,
        find: str,
        replace: str,
        context_before: str = "",
        context_after: str = "",
        track_changes: bool = True,
        author: str = "Coscribe",
        ignore_case: bool = False,
    ) -> dict[str, object]:
        file_path, document, host = self._open_for_tracked_edit(path)
        para_id = _locate_paragraph(
            host._document_element, find, context_before, context_after, ignore_case=ignore_case
        )
        result = host.replace_text(
            para_id,
            find=find,
            replace=replace,
            author=author,
            context_before=context_before,
            context_after=context_after,
            ignore_case=ignore_case,
            tracked=track_changes,
        )
        result.update(self._save_tracked_edit(file_path, document))
        return result

    @locked_by_path
    def accept_docx_tracked_changes(self, path: str, author: str = "") -> dict[str, object]:
        file_path, document, host = self._open_for_tracked_edit(path)
        result = host.accept_changes(author=author or None)
        result.update(self._save_tracked_edit(file_path, document))
        return result

    @locked_by_path
    def reject_docx_tracked_changes(self, path: str, author: str = "") -> dict[str, object]:
        file_path, document, host = self._open_for_tracked_edit(path)
        result = host.reject_changes(author=author or None)
        result.update(self._save_tracked_edit(file_path, document))
        return result
