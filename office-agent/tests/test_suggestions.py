"""What the model's answer to "what will the user type next" is made of."""

from coscribe.conversation.suggestions import clean_suggestion


def test_a_quoted_message_is_kept_as_one_line() -> None:
    assert clean_suggestion('"Make the table wider"\nbecause...') == "Make the table wider"
    assert clean_suggestion("“把第二张也补回来”") == "把第二张也补回来"


def test_none_or_nothing_is_no_suggestion() -> None:
    assert clean_suggestion("NONE") == ""
    assert clean_suggestion("none.") == ""
    assert clean_suggestion("  \n") == ""


def test_a_paragraph_is_not_a_suggestion() -> None:
    assert clean_suggestion("It seems that the user would probably want " * 6) == ""
