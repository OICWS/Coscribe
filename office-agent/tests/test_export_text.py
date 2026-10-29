from coscribe.conversation.export_text import conversation_markdown


def test_conversation_markdown_has_turns_and_tool_calls_and_shortens_long_results() -> None:
    entries = [
        {"kind": "user", "text": "make a deck"},
        {
            "kind": "tool",
            "tool_name": "write_file",
            "arguments": {"path": "a.svg"},
            "result": "x" * 5000,
            "is_error": True,
        },
        {"kind": "agent", "text": "done"},
    ]
    text = conversation_markdown("t_abc", entries)
    assert "# Conversation t_abc" in text
    assert "## You\n\nmake a deck" in text
    assert "### Tool: write_file (failed)" in text
    assert "more characters left out" in text
    assert text.index("## You") < text.index("### Tool") < text.index("## Coscribe\n\ndone")
