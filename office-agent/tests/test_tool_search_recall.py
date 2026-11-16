"""`search_tools` finds a hidden tool from the words a model would ask with.

The queries run against the real catalog: every tool a conversation registers that is not bound
to the model. A tool that cannot be found does not exist for the model, which then tells the
person the thing cannot be done. The first list was written before the word table
(`runtime_lg/search_words.py`), the second after it and without looking at it; the misses of
both are kept at the end so the number is not flattered.
"""

from __future__ import annotations

import json
from collections.abc import Callable

import pytest
from langchain_core.messages import AIMessage

from coscribe.coordinator import CORE_TOOL_NAMES
from coscribe.runtime_lg import build_search_tools_tool, tool_name
from coscribe.runtime_lg.search_words import query_words, tokenize

from .test_prompt_cache import _RecordingModel, _session

_FOUND = [
    ("excel formula", "write_xlsx_cells"),
    ("spreadsheet", "write_xlsx_cells"),
    ("create excel workbook", "write_xlsx_cells"),
    ("edit excel cell", "modify_xlsx"),
    ("recalculate formulas", "recalc_xlsx"),
    ("create word document", "write_docx"),
    ("word report", "write_docx"),
    ("track changes", "accept_docx_tracked_changes"),
    ("word comment", "edit_docx_review"),
    ("find and replace in word", "replace_docx_text"),
    ("insert picture into document", "add_docx_image"),
    ("create presentation", "write_pptx"),
    ("make slides", "write_pptx"),
    ("powerpoint", "write_pptx"),
    ("slide deck", "write_pptx"),
    ("speaker notes", "set_pptx_notes"),
    ("slide chart", "add_pptx_chart"),
    ("delete slide", "delete_pptx_slide"),
    ("slide preview image", "render_pptx_preview"),
    ("use template", "fill_pptx_template"),
    ("create pdf", "write_pdf"),
    ("convert to pdf", "convert_office_file"),
    ("export pdf", "convert_office_file"),
    ("run python", "run_python_script"),
    ("execute code", "run_python_script"),
    ("javascript", "run_node_script"),
    ("shell command", "run_background_command"),
    ("delete file", "delete_file"),
    ("rename file", "move_file"),
    ("remove file", "delete_file"),
    ("schedule", "create_scheduled_task"),
    ("recurring task every morning", "create_scheduled_task"),
    ("reminder", "sleep_until"),
    ("wait until tomorrow", "sleep_until"),
    ("sub-agent", "spawn_agent"),
    ("delegate research", "spawn_agent"),
    ("parallel workers", "spawn_agent_background"),
    ("save preference", "remember"),
    ("memory", "remember"),
    ("download image", "download_image"),
    ("find photo", "search_images"),
    ("stock photo", "search_licensed_images"),
    ("api call", "http_request"),
    ("POST request", "http_request"),
    ("previous conversation", "read_conversation"),
    ("chat history", "list_conversations"),
    ("search inside pdf", "search_pdf"),
    ("screenshot of page", "look_at_page"),
    ("生成PPT", "write_pptx"),
    ("定时任务", "create_scheduled_task"),
    ("表格", "write_xlsx_cells"),
    # Written after the word table, without looking at it.
    ("add a chart to the slides", "add_pptx_chart"),
    ("presentation template", "fill_pptx_template"),
    ("change slide text", "edit_pptx_text"),
    ("animation", "add_pptx_animation"),
    ("slide transition", "set_pptx_transition"),
    ("icons", "add_pptx_icon"),
    ("workbook formulas", "write_xlsx_cells"),
    ("update spreadsheet cells", "modify_xlsx"),
    ("accept revisions", "accept_docx_tracked_changes"),
    ("add heading to word file", "edit_docx_structure"),
    ("docx chart", "add_docx_chart"),
    ("pdf report", "write_pdf"),
    ("node", "run_node_script"),
    ("data analysis script", "run_python_script"),
    ("long running command", "run_background_command"),
    ("copy a file", "copy_file"),
    ("move files into folder", "move_file"),
    ("batch edit", "edit_file_batch"),
    ("every monday", "create_scheduled_task"),
    ("pause schedule", "pause_scheduled_task"),
    ("background agent", "spawn_agent_background"),
    ("check on agent", "check_subagent_task"),
    ("second opinion review", "review_work"),
    ("remember this", "remember"),
    ("image search", "search_images"),
    ("licensed images", "search_licensed_images"),
    ("other conversations", "list_conversations"),
    ("design system", "save_design_system"),
    ("render slide", "render_pptx_preview"),
    ("做一个演示文稿", "write_pptx"),
    ("把Word转换成PDF", "convert_office_file"),
    ("每天定时运行", "create_scheduled_task"),
    ("写Excel公式", "write_xlsx_cells"),
    ("运行Python脚本", "run_python_script"),
    # Missed by the second list when it was first run; the table has their words since.
    ("wake me later", "sleep_for"),
    ("call REST endpoint", "http_request"),
    ("credentials", "list_secrets"),
]

# Still not found: "to" is dropped as a filler word, and nothing else says a conversion.
_NOT_FOUND = [("word to pdf", "convert_office_file")]


@pytest.fixture(scope="module")
def search(tmp_path_factory: pytest.TempPathFactory) -> Callable[[str], list[str]]:
    root = tmp_path_factory.mktemp("recall")
    with pytest.MonkeyPatch.context() as patch:
        model = _RecordingModel(responses=[AIMessage(content="ok")])
        session = _session(root, patch, model, "recall", root / "folder")
        hidden = [
            tool
            for tool in session._build_lg_tools(model)  # noqa: SLF001
            if tool_name(tool) not in CORE_TOOL_NAMES
        ]
    search_tools = build_search_tools_tool(hidden)
    return lambda query: [match["name"] for match in json.loads(search_tools(query))]


@pytest.mark.parametrize(("query", "tool"), _FOUND, ids=[query for query, _ in _FOUND])
def test_a_tool_is_found_by_the_words_a_model_would_ask_with(
    search: Callable[[str], list[str]], query: str, tool: str
) -> None:
    assert tool in search(query)


@pytest.mark.parametrize(("query", "tool"), _NOT_FOUND, ids=[query for query, _ in _NOT_FOUND])
def test_the_known_misses_are_still_misses(
    search: Callable[[str], list[str]], query: str, tool: str
) -> None:
    """When this fails the search got better: move the query to the found list."""
    assert tool not in search(query)


def test_a_query_about_nothing_in_the_catalog_finds_nothing(
    search: Callable[[str], list[str]],
) -> None:
    assert search("book a flight to Paris") == []


def test_plurals_fold_and_a_query_gains_the_catalogs_words() -> None:
    assert tokenize("Slides and cells") == ["slide", "cell"]
    assert query_words("PowerPoint decks") == {"powerpoint", "deck", "pptx"}
    assert "xlsx" in query_words("做一个表格")
    assert query_words("帮我订机票") == set()
