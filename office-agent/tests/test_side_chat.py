from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from coscribe.conversation.side_chat import recent_part, side_prompt


def test_a_long_transcript_keeps_its_newest_part_from_a_heading_on() -> None:
    transcript = "## You\n\n" + "old " * 100 + "\n\n## Coscribe\n\nnewest answer"
    kept = recent_part(transcript, limit=60)
    assert kept.startswith("[Earlier messages left out]\n## Coscribe")
    assert kept.endswith("newest answer")
    assert recent_part("short", limit=60) == "short"


def test_the_side_messages_follow_the_transcript_in_their_roles() -> None:
    prompt = side_prompt(
        "## You\n\nhello",
        [
            {"role": "user", "text": "first"},
            {"role": "assistant", "text": "answer"},
            {"role": "user", "text": "second"},
        ],
    )
    assert isinstance(prompt[0], SystemMessage)
    assert "<conversation>\n## You\n\nhello\n</conversation>" in str(prompt[0].content)
    assert [type(m) for m in prompt[1:]] == [HumanMessage, AIMessage, HumanMessage]
