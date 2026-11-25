"""The language a new Word document is marked in, read straight from the house style."""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest
from docx import Document

from coscribe.tools.office.docx import _style
from coscribe.tools.office.docx.toolkit import DocxToolkit
from coscribe.tools.office.docx.tools import build_docx_tools

_W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


@pytest.mark.parametrize(
    ("language", "text", "expected"),
    [
        ("", "正文", "zh-CN"),
        ("", "これはテスト", "ja-JP"),
        ("", "본문", "ko-KR"),
        ("", "Plain text", "en-US"),
        ("zh", "", "zh-CN"),
        ("ZH-hant", "", "zh-TW"),
        ("zh-HK", "", "zh-TW"),
        ("ja", "", "ja-JP"),
        ("ko", "", "ko-KR"),
        (" en-gb ", "正文", "en-GB"),
        ("fr", "", "fr"),
    ],
)
def test_the_language_is_the_models_tag_else_the_texts_script(
    language: str, text: str, expected: str
) -> None:
    assert _style.document_language(language, text) == expected


@pytest.mark.parametrize("language", ["Chinese", "zh_CN", "z", "zh-"])
def test_a_language_that_is_not_a_tag_is_refused(language: str) -> None:
    with pytest.raises(ValueError, match="language tag"):
        _style.document_language(language, "")


def test_a_japanese_document_gets_the_japanese_face_and_theme() -> None:
    document = Document()
    _style.apply_house_style(document, language="ja-JP")

    defaults = document.styles.element.find(f"{_W}docDefaults")
    fonts = defaults.find(f".//{_W}rFonts")
    assert (fonts.get(f"{_W}eastAsia"), fonts.get(f"{_W}hint")) == ("游ゴシック", "eastAsia")
    assert defaults.find(f".//{_W}sz").get(f"{_W}val") == "21"
    heading = document.styles["Heading 1"].element.find(f".//{_W}rFonts")
    assert heading.get(f"{_W}eastAsia") == "游ゴシック"
    theme_lang = document.settings.element.find(f"{_W}themeFontLang")
    assert theme_lang.get(f"{_W}eastAsia") == "ja-JP"
    theme = document.part.part_related_by(
        "http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme"
    ).blob.decode()
    assert 'script="Jpan" typeface="游ゴシック"' in theme
    assert '<a:ea typeface="游ゴシック"/>' in theme
    assert 'script="Hans" typeface="游ゴシック"' not in theme


def test_a_latin_document_keeps_its_east_asian_settings_and_proofs_in_its_language() -> None:
    document = Document()
    _style.apply_house_style(document, language="de-DE")

    defaults = document.styles.element.find(f"{_W}docDefaults")
    assert defaults.find(f".//{_W}rFonts").get(f"{_W}hint") is None
    assert defaults.find(f".//{_W}lang").get(f"{_W}val") == "de-DE"
    assert defaults.find(f".//{_W}sz").get(f"{_W}val") == "22"
    theme_lang = document.settings.element.find(f"{_W}themeFontLang")
    assert theme_lang.get(f"{_W}val") == "de-DE"


def test_the_write_tool_hands_its_language_on(tmp_path: Path) -> None:
    (write_docx,) = (
        tool for tool in build_docx_tools(DocxToolkit(tmp_path)) if tool.__name__ == "write_docx"
    )
    assert inspect.signature(write_docx).parameters["language"].default == ""

    write_docx(path="k.docx", content="# 보고서", language="zh-TW")

    lang = Document(str(tmp_path / "k.docx")).styles.element.find(f".//{_W}lang")
    assert lang.get(f"{_W}eastAsia") == "zh-TW"
