from __future__ import annotations

from collections.abc import Callable
from typing import Any

from ....runtime import tool_metadata
from ..._output_truncation import cap_read_output
from .toolkit import DocxToolkit


# The tools are grouped into builders under 100 lines; `build_docx_tools` concatenates them in the
# original order, which is the tool-list order the schema snapshot pins.
def _docx_tools_1(toolkit: DocxToolkit) -> list[Callable[..., Any]]:
    def write_docx(
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
        """Create a Word (.docx) file under the workspace from structured text.

        Only when the person asked for Word or a .docx by name, gave a Word
        template, or wants tracked changes. Any other document (a report,
        resume, letter, plan, with tables and charts too) is a Doc: load the
        "Docs" skill and write a .md file instead; it exports to Word itself.

        `content` uses a light markdown subset: `#`/`##`/`###` for headings,
        `-`/`*` for bullet items, `1.` for numbered items, and
        `| cell | cell |` rows for tables. Plain lines become paragraphs.
        Two extra markers on top of that subset:

        - A line that is exactly `[TOC]` inserts a real Word table-of-
          contents field at that position, built from the document's own
          headings (levels 1-3, wherever they are in the content). It lists
          the headings in every viewer; Word adds the page numbers itself
          the first time the file is opened -- no manual "Update Field".
        - A trailing `{{comment: your comment text}}` on a heading,
          paragraph, bullet, or numbered-item line attaches a real Word
          comment (visible in Word's Comments pane) anchored to that whole
          line, authored as `comment_author`. Not recognized inside table
          cells.

        The response's `preview_path` (when the file can be drawn) names
        a rendered thumbnail of the first page the user can see in the
        chat UI -- not something to fetch or parse yourself.

        `template_path`, if given, is an existing .docx file (e.g. one with
        the user's own letterhead/styles/page setup) to build the new
        document on: its styles and page setup (size, margins) carry over.
        Without `track_changes`, its own body content is removed before the
        new content from `content` is added. With `track_changes=True`, the
        template's existing paragraphs are kept but marked as a tracked
        deletion instead (visible to the user as a reviewable redline, not
        silently discarded) -- tables in the template are still removed
        outright either way.

        `page_size` ("letter", "legal", "a4", or "a3") and `orientation`
        ("portrait" or "landscape") override the blank document's or
        template's page setup; leave either empty to keep the default.

        `track_changes=True` wraps every paragraph/bullet/heading this call
        writes in a tracked insertion (`w:ins`, authored as `change_author`)
        instead of writing it as already-final content -- use this when the
        document should go to a human as a reviewable redline they can
        accept/reject in Word, rather than a silent rewrite. Tables are
        always written as final content, not tracked, even with
        `track_changes=True` (documented scope limit -- table-level tracked
        changes need row/cell markup this tool doesn't generate).

        Args:
            path: file to write, relative to the workspace root
            content: document content in the markdown subset described above
            overwrite: whether to replace the file if it already exists
            template_path: optional .docx file to use as the document's
                starting styles/page-setup template, relative to the
                workspace root
            page_size: "letter", "legal", "a4", "a3", or empty to leave
                the current page size unchanged
            orientation: "portrait", "landscape", or empty to leave the
                current orientation unchanged
            track_changes: write this call's content as tracked
                insertions (and, with template_path, mark the template's
                old content as a tracked deletion instead of removing it)
            change_author: author name recorded on tracked-change markup
                when track_changes is True
            comment_author: author name recorded on `{{comment: ...}}`
                markers
        """
        return toolkit.write_docx(
            path=path,
            content=content,
            overwrite=overwrite,
            template_path=template_path,
            page_size=page_size,
            orientation=orientation,
            track_changes=track_changes,
            change_author=change_author,
            comment_author=comment_author,
        )

    return [
        tool_metadata(write_docx, risk_category="WRITE_LOCAL", category="documents"),
    ]


def _docx_tools_2(toolkit: DocxToolkit) -> list[Callable[..., Any]]:
    def add_docx_chart(
        path: str,
        chart_type: str,
        data: str,
        title: str = "",
        after_text: str = "",
        caption: str = "",
        width: float = 0.0,
        height: float = 3.2,
    ) -> dict[str, object]:
        """Add a native, editable chart to an existing Word (.docx) file.

        `data` is a pipe-table: the first column is the category axis and
        every other column is its own series named by its header cell, e.g.

            | Month | Revenue |
            | --- | --- |
            | Jan | 120 |
            | Feb | 135 |

        `chart_type` is "bar", "line" or "pie" (pie takes exactly one data
        column). The chart lands at the end of the document unless
        `after_text` names a paragraph (a heading's text works) to put it
        after. Everything else in the document is left as it is, so call
        this after `write_docx` -- writing the document again discards the
        chart. The result's `preview_path` shows the first page.

        Args:
            path: .docx file to edit, relative to the workspace root
            chart_type: "bar", "line" or "pie"
            data: pipe-table rows as described above
            title: chart title; empty for none
            after_text: text of the paragraph to place the chart after; it
                must match one paragraph. Empty puts the chart at the end.
            caption: optional italic line under the chart
            width: inches; 0 (default) fills the page's text width
            height: inches
        """
        return toolkit.add_docx_chart(
            path=path,
            chart_type=chart_type,
            data=data,
            title=title,
            after_text=after_text,
            caption=caption,
            width=width,
            height=height,
        )

    def add_docx_image(
        path: str,
        image_path: str,
        after_text: str = "",
        caption: str = "",
        width: float = 0.0,
    ) -> dict[str, object]:
        """Add a picture (PNG, JPEG, GIF or BMP) to an existing Word (.docx)
        file. It lands at the end of the document unless `after_text` names
        a paragraph to put it after; everything else is left as it is, so
        call this after `write_docx`. Use `add_docx_chart` for a chart from
        numbers -- it stays editable in Word.

        Args:
            path: .docx file to edit, relative to the workspace root
            image_path: image file, relative to the workspace root
            after_text: text of the paragraph to place the picture after; it
                must match one paragraph. Empty puts it at the end.
            caption: optional italic line under the picture
            width: inches; 0 (default) keeps the image's size, shrunk to the
                page's text width if larger
        """
        return toolkit.add_docx_image(
            path=path, image_path=image_path, after_text=after_text, caption=caption, width=width
        )

    return [
        tool_metadata(add_docx_chart, risk_category="WRITE_LOCAL", category="documents"),
        tool_metadata(add_docx_image, risk_category="WRITE_LOCAL", category="documents"),
    ]


def _docx_tools_3(toolkit: DocxToolkit) -> list[Callable[..., Any]]:
    def insert_docx_text(
        path: str,
        text: str,
        context_before: str,
        context_after: str = "",
        track_changes: bool = True,
        author: str = "Coscribe",
        ignore_case: bool = False,
    ) -> dict[str, object]:
        """Insert text into an existing Word (.docx) file, in place.

        Edits the real document tree directly -- headers/footers, other
        paragraphs, tables, and images are left completely untouched,
        unlike `write_docx` (which regenerates the whole document from a
        markdown subset and would silently drop anything that subset can't
        represent). The target location is found from `context_before` --
        the existing text to insert immediately after -- not a paragraph
        number or id; this must be unique in the document, or use
        `context_after` (text immediately following the insertion point)
        to disambiguate.

        With `track_changes=True` (the default), the inserted text is
        wrapped in `<w:ins>` tracked-changes markup Word shows in its
        Review pane, rather than becoming final text immediately -- use
        `track_changes=False` for a plain, silent edit.

        Args:
            path: existing .docx file to edit, relative to the workspace root
            text: the text to insert
            context_before: existing document text to insert immediately
                after -- required, and must be unique (with context_after
                to disambiguate if it appears more than once)
            context_after: existing text immediately following the
                insertion point, to disambiguate when context_before alone
                is not unique
            track_changes: insert as a reviewable tracked change (default)
                rather than a plain, already-final edit
            author: author name recorded on the tracked-change markup, when
                track_changes is True
            ignore_case: match context_before/context_after case-insensitively
        """
        return toolkit.insert_docx_text(
            path=path,
            text=text,
            context_before=context_before,
            context_after=context_after,
            track_changes=track_changes,
            author=author,
            ignore_case=ignore_case,
        )

    return [
        tool_metadata(insert_docx_text, risk_category="WRITE_LOCAL", category="documents"),
    ]


def _docx_tools_4(toolkit: DocxToolkit) -> list[Callable[..., Any]]:
    def delete_docx_text(
        path: str,
        text: str,
        context_before: str = "",
        context_after: str = "",
        track_changes: bool = True,
        author: str = "Coscribe",
        ignore_case: bool = False,
    ) -> dict[str, object]:
        """Delete text from an existing Word (.docx) file, in place.

        Edits the real document tree directly -- headers/footers, other
        paragraphs, tables, and images are left completely untouched,
        unlike `write_docx` (which regenerates the whole document from a
        markdown subset and would silently drop anything that subset can't
        represent). `text` must be unique in the document; use
        `context_before`/`context_after` (surrounding text) to disambiguate
        if it appears more than once.

        With `track_changes=True` (the default), the text is wrapped in
        `<w:del>` tracked-changes markup Word shows in its Review pane
        (strikethrough) rather than being removed immediately -- use
        `track_changes=False` to remove it outright.

        Args:
            path: existing .docx file to edit, relative to the workspace root
            text: the exact text to delete
            context_before: text immediately before `text`, to disambiguate
                if it appears more than once
            context_after: text immediately after `text`, to disambiguate
                if it appears more than once
            track_changes: mark as a reviewable tracked deletion (default)
                rather than removing the text outright
            author: author name recorded on the tracked-change markup, when
                track_changes is True
            ignore_case: match text/context case-insensitively
        """
        return toolkit.delete_docx_text(
            path=path,
            text=text,
            context_before=context_before,
            context_after=context_after,
            track_changes=track_changes,
            author=author,
            ignore_case=ignore_case,
        )

    return [
        tool_metadata(delete_docx_text, risk_category="WRITE_LOCAL", category="documents"),
    ]


def _docx_tools_5(toolkit: DocxToolkit) -> list[Callable[..., Any]]:
    def replace_docx_text(
        path: str,
        find: str,
        replace: str,
        context_before: str = "",
        context_after: str = "",
        track_changes: bool = True,
        author: str = "Coscribe",
        ignore_case: bool = False,
    ) -> dict[str, object]:
        """Replace text in an existing Word (.docx) file, in place.

        Edits the real document tree directly -- headers/footers, other
        paragraphs, tables, and images are left completely untouched,
        unlike `write_docx` (which regenerates the whole document from a
        markdown subset and would silently drop anything that subset can't
        represent). `find` must be unique in the document; use
        `context_before`/`context_after` to disambiguate if it appears
        more than once.

        With `track_changes=True` (the default), marks only the actually-
        changed portion of `find` as a tracked deletion+insertion (e.g.
        replacing "red" with "blue" in "the red car" tracks just "red" ->
        "blue", not the whole sentence) -- use `track_changes=False` for a
        plain, silent edit.

        Args:
            path: existing .docx file to edit, relative to the workspace root
            find: the exact existing text to replace
            replace: the new text
            context_before: text immediately before `find`, to disambiguate
                if it appears more than once
            context_after: text immediately after `find`, to disambiguate
                if it appears more than once
            track_changes: mark as a reviewable tracked change (default)
                rather than a plain, already-final edit
            author: author name recorded on the tracked-change markup, when
                track_changes is True
            ignore_case: match find/context case-insensitively
        """
        return toolkit.replace_docx_text(
            path=path,
            find=find,
            replace=replace,
            context_before=context_before,
            context_after=context_after,
            track_changes=track_changes,
            author=author,
            ignore_case=ignore_case,
        )

    def accept_docx_tracked_changes(path: str, author: str = "") -> dict[str, object]:
        """Accept tracked changes in an existing Word (.docx) file.

        Insertions become permanent text; deletions are permanently
        removed. Leave `author` empty to accept every tracked change in the
        document, or name one author to accept only that author's changes
        and leave everyone else's still pending review.

        Args:
            path: existing .docx file to edit, relative to the workspace root
            author: accept only this author's changes, or empty for all
        """
        return toolkit.accept_docx_tracked_changes(path=path, author=author)

    def reject_docx_tracked_changes(path: str, author: str = "") -> dict[str, object]:
        """Reject tracked changes in an existing Word (.docx) file.

        Insertions are discarded; deletions are restored. Leave `author`
        empty to reject every tracked change in the document, or name one
        author to reject only that author's changes and leave everyone
        else's still pending review.

        Args:
            path: existing .docx file to edit, relative to the workspace root
            author: reject only this author's changes, or empty for all
        """
        return toolkit.reject_docx_tracked_changes(path=path, author=author)

    return [
        tool_metadata(replace_docx_text, risk_category="WRITE_LOCAL", category="documents"),
        tool_metadata(
            accept_docx_tracked_changes, risk_category="WRITE_LOCAL", category="documents"
        ),
        tool_metadata(
            reject_docx_tracked_changes, risk_category="WRITE_LOCAL", category="documents"
        ),
    ]


def build_docx_tools(toolkit: DocxToolkit) -> list[Callable[..., Any]]:
    """The Word tools, bound to `toolkit`."""

    return [
        _read_docx_tool(toolkit),
        *_docx_tools_1(toolkit),
        *_docx_tools_2(toolkit),
        *_docx_tools_3(toolkit),
        *_docx_tools_4(toolkit),
        *_docx_tools_5(toolkit),
        _edit_docx_structure_tool(toolkit),
        *_docx_review_tools(toolkit),
    ]


def _docx_review_tools(toolkit: DocxToolkit) -> list[Callable[..., Any]]:
    def read_docx_review(path: str) -> dict[str, object]:
        """List a Word (.docx) file's tracked changes and comments, each with
        the id that `edit_docx_review` takes.

        `changes` are the insertions and deletions in document order, with
        their author, date, text and the heading they fall under;
        `other_changes` counts the rest (moves, formatting changes), which
        only Word can act on one by one. `comments` are the comment threads,
        each with the words it is anchored to, whether it is resolved
        (`done`), and its replies.

        Args:
            path: .docx file, relative to the workspace root
        """
        return toolkit.read_docx_review(path=path)

    def edit_docx_review(
        path: str, operations: list[dict[str, str]], author: str = "Coscribe"
    ) -> dict[str, object]:
        """Act on a Word (.docx) file's review, the way a reviewer in Word
        would: accept or reject single tracked changes, reply to, resolve or
        reopen comments, or comment on some words. Ids come from
        `read_docx_review`.

        `operations` run in order, each a dict with an `op`:

        - `{"op": "accept", "change": "<id>"}` / `{"op": "reject", "change": "<id>"}`
        - `{"op": "accept_all"}` / `{"op": "reject_all"}`
        - `{"op": "reply", "comment": "<id>", "text": "..."}`
        - `{"op": "resolve", "comment": "<id>"}` / `{"op": "reopen", "comment": "<id>"}`:
          the whole thread
        - `{"op": "comment", "on": "<words>", "text": "..."}`: a new comment on
          words that appear exactly once in the document

        If any operation fails, nothing is saved.

        Args:
            path: existing .docx file, relative to the workspace root
            operations: the actions, in order
            author: name shown on new comments and replies
        """
        return toolkit.edit_docx_review(path=path, operations=operations, author=author)

    return [
        tool_metadata(read_docx_review, risk_category="READ", category="documents"),
        tool_metadata(edit_docx_review, risk_category="WRITE_LOCAL", category="documents"),
    ]


def _edit_docx_structure_tool(toolkit: DocxToolkit) -> Callable[..., Any]:
    """Kept out of `build_docx_tools`, which already holds every other Word tool."""

    def edit_docx_structure(
        path: str,
        operations: list[dict[str, str]],
        output_path: str = "",
        track_changes: bool = False,
        author: str = "Coscribe",
    ) -> dict[str, object]:
        """Restructure an existing Word (.docx) file in one call: add headed
        sections, lists, tables or a contents list, move a section, delete a
        section. Everything not named is left as it is -- styles, headers,
        pictures, charts, other tables -- unlike `write_docx`, which rebuilds
        the whole file. Use this rather than a script for any change to a
        document's structure; use `replace_docx_text` for wording.

        `operations` run in order, each a dict with an `op`:

        - `{"op": "insert", "content": "...", <place>}`: `content` in
          write_docx's markdown subset (#/##/### headings, - bullets, 1.
          numbered items, | pipe | tables |, and a `[TOC]` line for a contents
          list). It takes the document's own heading and list styles, and new
          tables the style of its existing ones.
        - `{"op": "move_section", "section": "<heading>", <place>}`: the
          heading and everything under it, up to the next heading of the same
          or a higher level.
        - `{"op": "delete_section", "section": "<heading>"}`.

        `<place>` is exactly one of `"after": "<paragraph text>"`,
        `"before": "<paragraph text>"` or `"after_section": "<heading>"`
        (after everything under that heading). Text is matched exactly, or
        else as part of one paragraph; it must name one. A contents list is
        filled from all the document's headings once every operation has run.
        If any operation fails, nothing is saved. The result's `document`
        lists the edited file's headings in order, its tables, pictures,
        header, footer and contents list -- enough to check the edit without
        opening the file.

        Args:
            path: existing .docx file, relative to the workspace root
            operations: the edits, in order
            output_path: save to this new file instead and leave `path` as it
                is; it must not exist yet
            track_changes: show inserted and deleted text as tracked changes
                for review (a move can't be tracked)
            author: name shown on tracked changes
        """
        return toolkit.edit_docx_structure(
            path=path,
            operations=operations,
            output_path=output_path,
            track_changes=track_changes,
            author=author,
        )

    return tool_metadata(edit_docx_structure, risk_category="WRITE_LOCAL", category="documents")


def _read_docx_tool(toolkit: DocxToolkit) -> Callable[..., Any]:
    """Kept out of `build_docx_tools`, which already holds every other Word tool."""

    def read_docx(path: str, view: str = "text") -> str:
        """Read a Word (.docx) file under the workspace as markdown.

        Headings, lists, tables, links, and bold/italic all come through as
        their markdown equivalents. `view="structure"` lists instead each
        block's style, tables with their style, pictures, contents lists,
        and each section's page, header and footer: use it to check a
        document before and after an edit, rather than a script.

        Args:
            path: file to read, relative to the workspace root
            view: "text" (markdown) or "structure"
        """
        return cap_read_output(
            toolkit.read_docx(path=path, view=view),
            "search_files or a script (python-docx) reaches the rest without reading it all",
        )

    return tool_metadata(read_docx, risk_category="READ", category="documents")
