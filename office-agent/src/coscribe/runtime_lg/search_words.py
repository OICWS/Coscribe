"""The words `search_tools` matches on: a query's tokens, plus the words tool names use for them.

Tool names are literal (`write_pptx`, `run_node_script`), and a model asks in its own words
("powerpoint", "spreadsheet", "javascript", "幻灯片"). Measured on the real catalog with 52 such
queries, matching the query's words alone found the tool for 32; the misses returned nothing, and
the model then concluded the thing could not be done. The table is small on purpose: it holds
only what a name or description in the catalog says in another word.
"""

from __future__ import annotations

import re

_STOPWORDS = frozenset(
    {"a", "an", "the", "to", "of", "for", "and", "or", "in", "on", "with", "this", "that",
     "is", "are", "it", "as", "at", "be", "by", "from", "into"}
)  # fmt: skip
_TOKEN_RE = re.compile(r"[a-z0-9]+")

# A word a model asks with, and the words the catalog's names use for it.
_SAME_AS: dict[str, tuple[str, ...]] = {
    "powerpoint": ("pptx",),
    "ppt": ("pptx",),
    "presentation": ("pptx",),
    "deck": ("pptx",),
    "slide": ("pptx",),
    "excel": ("xlsx",),
    "spreadsheet": ("xlsx",),
    "workbook": ("xlsx",),
    "sheet": ("xlsx",),
    "word": ("docx",),
    "document": ("docx",),
    "picture": ("image",),
    "photo": ("image",),
    "javascript": ("node",),
    "js": ("node",),
    "code": ("script",),
    "execute": ("run",),
    "shell": ("command",),
    "terminal": ("command",),
    "reminder": ("wake", "sleep"),
    "wait": ("sleep",),
    "memory": ("remember",),
    "preference": ("remember",),
    "delegate": ("agent", "spawn"),
    "subagent": ("agent", "spawn"),
    "worker": ("agent", "spawn"),
    "parallel": ("background",),
    "api": ("http",),
    "rest": ("http",),
    "endpoint": ("http",),
    "credential": ("secret",),
    "password": ("secret",),
    "later": ("sleep",),
    "history": ("conversation",),
    "chat": ("conversation",),
    "recurring": ("scheduled",),
    "schedule": ("scheduled",),
    "cron": ("scheduled",),
    "rename": ("move",),
    "remove": ("delete",),
    "export": ("convert",),
    "screenshot": ("look", "render", "preview"),
}

# A query in Chinese has no token the names could match; these are found as substrings.
_CHINESE: dict[str, tuple[str, ...]] = {
    "幻灯片": ("pptx",),
    "演示": ("pptx",),
    "表格": ("xlsx",),
    "工作簿": ("xlsx",),
    "公式": ("formula", "xlsx"),
    "文档": ("docx",),
    "图表": ("chart",),
    "图片": ("image",),
    "照片": ("image",),
    "脚本": ("script",),
    "代码": ("script",),
    "定时": ("scheduled",),
    "计划任务": ("scheduled",),
    "提醒": ("wake", "sleep"),
    "记住": ("remember",),
    "记忆": ("remember",),
    "子代理": ("agent", "spawn"),
    "委派": ("agent", "spawn"),
    "模板": ("template",),
    "批注": ("review",),
    "修订": ("tracked",),
    "删除": ("delete",),
    "转换": ("convert",),
    "技能": ("skill",),
}


def _singular(word: str) -> str:
    if len(word) > 3 and word.endswith("s") and not word.endswith("ss"):
        return word[:-1]
    return word


def tokenize(text: str) -> list[str]:
    """The words of a name or a description, plurals folded so "slides" finds "slide"."""
    return [
        _singular(word)
        for word in _TOKEN_RE.findall(text.lower())
        if len(word) > 1 and word not in _STOPWORDS
    ]


def query_words(query: str) -> set[str]:
    """A query's own words and the catalog's words for them."""
    words = set(tokenize(query))
    for word in list(words):
        words.update(_SAME_AS.get(word, ()))
    for phrase, same in _CHINESE.items():
        if phrase in query:
            words.update(same)
    return words
