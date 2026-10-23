"""Unit tests for runtime_lg/messages.py's pure helpers -- see
test_web.py's test_reconnect_replays_a_sent_images_data_urls_lg for the
full WS-round-trip regression test this complements."""

from langchain_core.messages import AIMessage, HumanMessage

from coscribe.runtime_lg.messages import (
    AUTO_MODE_NOTE,
    artifact_note,
    extract_images,
    language_note,
    serialize_history_for_ws_lg,
    strip_mode_note,
)

_DATA_URL_1 = "data:image/png;base64,aGVsbG8="
_DATA_URL_2 = "data:image/png;base64,d29ybGQ="


def test_extract_images_pulls_image_url_blocks_in_order() -> None:
    content = [
        {"type": "text", "text": "what's in these?"},
        {"type": "image_url", "image_url": {"url": _DATA_URL_1}},
        {"type": "image_url", "image_url": {"url": _DATA_URL_2}},
    ]
    assert extract_images(content) == [_DATA_URL_1, _DATA_URL_2]


def test_extract_images_is_empty_for_a_plain_string_content() -> None:
    assert extract_images("just text, no images") == []


def test_serialize_history_includes_images_on_a_user_entry() -> None:
    messages = [
        HumanMessage(
            content=[
                {"type": "text", "text": "what's in this?"},
                {"type": "image_url", "image_url": {"url": _DATA_URL_1}},
            ]
        ),
        AIMessage(content="a cat"),
    ]
    assert serialize_history_for_ws_lg(messages) == [
        {"kind": "user", "text": "what's in this?", "images": [_DATA_URL_1]},
        {"kind": "agent", "text": "a cat"},
    ]


def test_serialize_history_keeps_an_image_only_send_no_caption() -> None:
    # Real edge case the fix had to account for: the old `if not text:
    # continue` guard ran *before* any image was ever looked at, so a
    # send with no caption text dropped the whole entry, image included.
    messages = [
        HumanMessage(content=[{"type": "image_url", "image_url": {"url": _DATA_URL_1}}]),
        AIMessage(content="a dog"),
    ]
    assert serialize_history_for_ws_lg(messages) == [
        {"kind": "user", "text": "", "images": [_DATA_URL_1]},
        {"kind": "agent", "text": "a dog"},
    ]


def test_serialize_history_omits_images_key_for_a_text_only_message() -> None:
    messages = [HumanMessage(content="hello"), AIMessage(content="hi")]
    entries = serialize_history_for_ws_lg(messages)
    assert "images" not in entries[0]


def test_strip_mode_note_removes_current_and_old_date_note_formats() -> None:
    # A checkpointed thread can carry either format depending on when its
    # HumanMessages were written, so both must strip cleanly.
    assert strip_mode_note("Today's real date is 2026-09-26. hello") == "hello"
    new_format = "Today's real date is 2026-09-26 (Saturday); local time 14:05 (UTC+08:00). hello"
    assert strip_mode_note(new_format) == "hello"


def test_language_note_names_the_language_of_a_cjk_message() -> None:
    assert "Chinese" in language_note("看一下 Q3资料 里的 客户主数据.csv 和 汇率_2026Q3.csv")
    assert "Japanese" in language_note("この資料をまとめてください")
    assert "Korean" in language_note("이 파일을 요약해 주세요")
    assert language_note("Summarize the Q3 sales file") == ""
    assert language_note("Summarize 客户主数据.csv and the exchange rates for Q3 please") == ""


def test_strip_mode_note_also_removes_the_language_note() -> None:
    sent = "Today's real date is 2026-10-05 (Monday); local time 09:00 (UTC+08:00). "
    sent += AUTO_MODE_NOTE + language_note("帮我做 Q3 经营回顾") + "帮我做 Q3 经营回顾"

    assert strip_mode_note(sent) == "帮我做 Q3 经营回顾"


def test_artifact_note_names_what_is_made_and_is_stripped_from_history() -> None:
    note = artifact_note("slides")
    assert "Slides artifact" in note and "instructions for new decks" in note
    assert artifact_note("docs").startswith("[The user is starting a Docs artifact: ")
    assert (
        artifact_note("sheets") and artifact_note(None) == "" and artifact_note("dashboard") == ""
    )
    assert strip_mode_note(note + "a deck about tea") == "a deck about tea"
    design = artifact_note("design")
    assert "SVG and HTML Design skill" in design
    assert strip_mode_note(design + "an icon for tea") == "an icon for tea"
    system = artifact_note("design-system")
    assert "save_design_system" in system and system.startswith("[The user is starting a Design-")
    assert strip_mode_note(system + "a calm look for a law firm") == "a calm look for a law firm"
    # After the date and mode notes, ahead of the language note, as the session writes them.
    asked = "做一个关于茶的演示"
    full = f"Today's real date is 2026-10-22. {AUTO_MODE_NOTE}{note}{language_note(asked)}{asked}"
    assert strip_mode_note(full) == asked


def test_a_slides_note_carries_the_chosen_design_system_in_one_stripped_sentence() -> None:
    system = {
        "name": "Acme [draft]",
        "overview": "Calm\nand technical.",
        "colors": [{"name": "Brand", "value": "#112233", "note": "Logo and key figures"}],
        "typography": {
            "fonts": ["Inter"],
            "styles": [{"name": "Body", "size": 32, "weight": 400}],
        },
        "spacing": [{"name": "Gap", "value": "24"}],
        "radius": [],
    }
    note = artifact_note("slides", system)
    assert 'Follow their design system "Acme [draft)".' in note
    assert "Overview: Calm and technical." in note
    assert "Brand #112233 (Logo and key figures)" in note and "Fonts: Inter." in note
    assert "Body 32px weight 400" in note and "Spacing: Gap 24." in note
    assert "Corner radius" not in note
    assert strip_mode_note(note + "a deck about tea") == "a deck about tea"
    # Only a Slides conversation takes one, and none changes the note.
    assert artifact_note("docs", system) == artifact_note("docs")
    assert artifact_note("slides", None) == artifact_note("slides")


def test_the_note_naming_attached_files_becomes_the_entrys_files_not_its_text() -> None:
    from coscribe.runtime_lg import split_attached_files

    note = "(Attached files, now in the workspace: a.xlsx, notes/b.py)"
    assert split_attached_files(f"look at these\n\n{note}") == (
        "look at these",
        ["a.xlsx", "notes/b.py"],
    )
    assert split_attached_files(note) == ("", ["a.xlsx", "notes/b.py"])
    assert split_attached_files("no files (Attached files, now in the workspace) here") == (
        "no files (Attached files, now in the workspace) here",
        [],
    )
    messages = [HumanMessage(content=f"look at these\n\n{note}"), HumanMessage(content=note)]
    assert serialize_history_for_ws_lg(messages) == [
        {"kind": "user", "text": "look at these", "files": ["a.xlsx", "notes/b.py"]},
        {"kind": "user", "text": "", "files": ["a.xlsx", "notes/b.py"]},
    ]
