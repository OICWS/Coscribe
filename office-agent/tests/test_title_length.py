"""The title the model gives a conversation fits a sidebar row."""

from coscribe.conversation.turn_text import clean_title


def test_a_short_title_is_kept_as_it_is() -> None:
    assert clean_title('"Q3 sales summary"') == "Q3 sales summary"
    assert clean_title("Q3 销售汇总。") == "Q3 销售汇总"


def test_a_sentence_is_cut_at_a_word_with_an_ellipsis() -> None:
    title = clean_title(
        "Reading the attached contract for termination clauses, notice periods and penalties"
    )

    assert title.endswith("…")
    assert len(title) <= 41
    assert " " not in title[-3:]  # not in the middle of a word it could have kept whole


def test_chinese_counts_double_and_only_the_first_line_is_used() -> None:
    first_line = "请帮我把第三季度的销售数据汇总成一张表格并且按地区分组然后做成图表发给我"
    title = clean_title(f"{first_line}\nsecond line")

    assert title.endswith("…")
    assert len(title) <= 21
    assert "second" not in title


def test_a_bare_tool_call_tag_is_no_title() -> None:
    assert clean_title("<tool_call>") == ""
    assert clean_title("</tool_call>") == ""
    assert clean_title("<｜tool▁calls▁begin｜>") == ""


def test_a_tool_call_written_as_text_is_no_title() -> None:
    call = '{"name": "read_file", "arguments": {"path": "a.xlsx"}}'
    assert clean_title(f"<tool_call>\n{call}\n</tool_call>") == ""
    deepseek = "<｜tool▁calls▁begin｜><｜tool▁call▁begin｜>function<｜tool▁sep｜>read_file"
    assert clean_title(deepseek + '\n{"path": "a"}') == ""
    assert clean_title('{"name": "read_file", "arguments": {}}') == ""


def test_the_title_before_a_tool_call_is_kept() -> None:
    assert clean_title('Q3 销售汇总\n<tool_call>{"name": "read_file"}</tool_call>') == "Q3 销售汇总"
    assert clean_title("Q3 sales summary <tool_call>") == "Q3 sales summary"


def test_reasoning_and_markup_around_the_title_are_dropped() -> None:
    reasoning = "<think>\nThe user wants a summary of sales.\n</think>\n\n"
    assert clean_title(reasoning + "Q3 sales summary") == "Q3 sales summary"
    assert clean_title("<think>still thinking about it") == ""
    assert clean_title("<title>Q3 sales summary</title>") == "Q3 sales summary"
    assert clean_title("<｜end▁of▁sentence｜>") == ""


def test_a_comparison_in_the_title_is_not_taken_for_markup() -> None:
    assert clean_title("Check if a < b and c > d") == "Check if a < b and c > d"
