"""The Doc artifact's source (decision 0025): a markdown file read as blocks and changed one block
at a time, and the chart block it can hold."""

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

__all__ = [
    "CALLOUTS",
    "Block",
    "BlocksRefused",
    "Chart",
    "Delete",
    "Doc",
    "Edit",
    "Insert",
    "NotADoc",
    "Replace",
    "apply_edits",
    "is_doc",
    "parse_chart",
    "read_doc",
]
