"""The Doc artifact's source (decision 0025): a markdown file read as blocks and changed one block
at a time, the chart block it can hold, and the file as the editor reads and saves it, with its kept
versions and what the person changed since coscribe was told."""

from __future__ import annotations

from .blocks import (
    CALLOUTS,
    Block,
    BlocksRefused,
    Delete,
    Doc,
    Edit,
    Insert,
    NotADoc,
    Replace,
    apply_edits,
    is_doc,
    read_doc,
)
from .chart import Chart, parse_chart
from .comments import (
    DocCommentNotFound,
    DocCommentRefused,
    add_doc_comment,
    delete_doc_comment,
    edit_doc_comment,
    mark_doc_comment_sent,
    read_doc_comments,
    reply_to_doc_comment,
    resolve_doc_comment,
)
from .files import DocFileChanged, read_doc_file, save_doc_edits
from .history import VersionGone as DocVersionGone
from .history import remember_version as remember_doc_version
from .history import restore_version as restore_doc_version
from .told import edits_since_told as doc_edits_since_told
from .told import remember_before_edit as remember_doc_before_edit

__all__ = [
    "CALLOUTS",
    "DocCommentNotFound",
    "DocCommentRefused",
    "DocFileChanged",
    "DocVersionGone",
    "Block",
    "BlocksRefused",
    "Chart",
    "Delete",
    "Doc",
    "Edit",
    "Insert",
    "NotADoc",
    "Replace",
    "add_doc_comment",
    "apply_edits",
    "delete_doc_comment",
    "edit_doc_comment",
    "doc_edits_since_told",
    "is_doc",
    "parse_chart",
    "read_doc",
    "mark_doc_comment_sent",
    "read_doc_comments",
    "read_doc_file",
    "remember_doc_before_edit",
    "remember_doc_version",
    "reply_to_doc_comment",
    "resolve_doc_comment",
    "restore_doc_version",
    "save_doc_edits",
]
