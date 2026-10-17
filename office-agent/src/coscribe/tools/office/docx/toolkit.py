from __future__ import annotations

from pathlib import Path
from typing import Any

from ..._file_locks import locked_by_path
from ..._ooxml_validate import assert_wml_valid
from ..._thumbnail import render_thumbnail
from ..toolkit import WorkspaceToolkit
from ._review import edit_review, read_review, write_atomically
from ._structure import add_blocks, apply_operations, describe, finish_tocs, summary
from ._style import TITLE_STYLE, apply_house_style, has_cjk
from ._xml import (
    _apply_page_setup,
    _build_comments_xml,
    _ChangeIdCounter,
    _clear_body,
    _locate_paragraph,
    _mark_body_deleted,
    _new_comment_anchor,
    _text_column_emu,
    _toc_result_paragraphs,
    _TrackedDocxHost,
    _write_comments_part,
)


def _title_first_heading(document: Any, written: Any) -> None:
    """A document that opens with a `#` heading opens with its title: set in the Title style,
    it stands apart from the section headings and stays out of a contents list."""
    from docx.oxml.ns import qn

    first = written.elements[0] if written.elements else None
    style = first.find(f"{qn('w:pPr')}/{qn('w:pStyle')}") if first is not None else None
    if style is None or style.get(qn("w:val")) != "Heading1":
        return
    style.set(qn("w:val"), document.styles[TITLE_STYLE].style_id)
    written.headings.pop(0)


class DocxToolkit(WorkspaceToolkit):
    @locked_by_path
    def read_docx(self, path: str, view: str = "text") -> str:
        import mammoth
        from markdownify import markdownify

        file_path = self._check_readable(path)
        if view == "structure":
            from docx import Document

            return describe(Document(str(file_path)))
        if view != "text":
            raise ValueError('view is "text" or "structure"')
        with file_path.open("rb") as docx_file:
            # A document's title reads back as `#`, the way write_docx takes it.
            html = mammoth.convert_to_html(
                docx_file, style_map="p[style-name='Title'] => h1:fresh"
            ).value
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
            apply_house_style(document, cjk=has_cjk(content))

        if page_size or orientation:
            _apply_page_setup(document, page_size, orientation)
        author = change_author if track_changes else None
        written = add_blocks(document, content, author, change_ids)
        if not template_path:
            _title_first_heading(document, written)
        # Written only now, so the TOC also lists the headings after its marker.
        has_toc = finish_tocs(document, written.tocs, written.headings, author, change_ids)
        pending_comments = written.comments
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
    def edit_docx_structure(
        self,
        path: str,
        operations: list[dict[str, str]],
        output_path: str = "",
        track_changes: bool = False,
        author: str = "Coscribe",
    ) -> dict[str, object]:
        from docx import Document
        from docx.oxml.ns import qn

        if not operations:
            raise ValueError("operations is empty")
        source = self._check_readable(path) if output_path else self._check_editable(path)
        target = self._check_writable(output_path, overwrite=False) if output_path else source
        document = Document(str(source))
        # Word needs revision ids unique across the document, the user's own included.
        ids = [int(v) for e in document.element.iter() if (v := e.get(qn("w:id"), "")).isdigit()]
        change_ids = _ChangeIdCounter(max(ids, default=0) + 1)
        done = apply_operations(document, operations, author if track_changes else None, change_ids)
        assert_wml_valid(document.element, "edit_docx_structure")
        document.save(str(target))
        preview_path, preview_skipped_reason = render_thumbnail(target, self._state_dir)
        return {
            "path": self._scope.relative(target),
            "bytes_written": target.stat().st_size,
            "done": done,
            "document": summary(document),
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
        # anchor among the others, not counting a TOC's copies of headings.
        skipped = {paragraph._p, last._p} | _toc_result_paragraphs(document.element.body)  # noqa: SLF001
        others = [p for p in document.paragraphs if p._p not in skipped]  # noqa: SLF001
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

    @locked_by_path
    def read_docx_review(self, path: str) -> dict[str, object]:
        file_path = self._check_readable(path)
        return {"path": self._scope.relative(file_path), **read_review(file_path.read_bytes())}

    @locked_by_path
    def edit_docx_review(
        self, path: str, operations: list[dict[str, Any]], author: str = "Coscribe"
    ) -> dict[str, object]:
        file_path = self._check_editable(path)
        data, done = edit_review(file_path.read_bytes(), operations, author)
        write_atomically(file_path, data)
        review = read_review(data)
        preview_path, preview_skipped_reason = render_thumbnail(file_path, self._state_dir)
        return {
            "path": self._scope.relative(file_path),
            "done": done,
            "changes_left": len(review["changes"]),
            "open_comments": sum(1 for c in review["comments"] if not c["done"]),
            "preview_path": preview_path,
            "preview_skipped_reason": preview_skipped_reason,
        }
