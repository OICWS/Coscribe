"""Finding a LibreOffice (decision 0026): coscribe's own copy first, then an installed one."""

from __future__ import annotations

import stat
import sys
from pathlib import Path

import pytest

from coscribe.tools import find_libreoffice, libreoffice_status
from coscribe.tools import libreoffice as lo

pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="fake launchers are shell scripts")


def _launcher(folder: Path, text: str = "LibreOffice 26.8.1.1 abc123") -> Path:
    path = folder / "program" / "soffice"
    path.parent.mkdir(parents=True)
    path.write_text(f'#!/bin/sh\necho "{text}"\n')
    path.chmod(path.stat().st_mode | stat.S_IXUSR)
    return path


@pytest.fixture(autouse=True)
def _nothing_installed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(lo.shutil, "which", lambda name: None)
    lo._version_of.cache_clear()


def test_a_computer_without_libreoffice_is_not_an_error(tmp_path: Path) -> None:
    assert find_libreoffice(tmp_path) is None
    assert libreoffice_status(tmp_path) == {
        "found": False,
        "source": None,
        "path": None,
        "version": None,
    }


def test_coscribes_own_copy_is_found_and_reports_its_version(tmp_path: Path) -> None:
    launcher = _launcher(tmp_path / "libreoffice" / "26.8.1")
    assert find_libreoffice(tmp_path) == (launcher, "own")
    assert libreoffice_status(tmp_path) == {
        "found": True,
        "source": "own",
        "path": str(launcher),
        "version": "26.8.1.1",
    }


def test_an_installed_copy_is_found_on_the_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    launcher = _launcher(tmp_path / "system")
    monkeypatch.setattr(
        lo.shutil, "which", lambda name: str(launcher) if name == "soffice" else None
    )
    assert find_libreoffice(tmp_path / "state") == (launcher, "system")


def test_own_copy_wins_over_an_installed_one(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    system = _launcher(tmp_path / "system")
    monkeypatch.setattr(lo.shutil, "which", lambda name: str(system))
    own = _launcher(tmp_path / "state" / "libreoffice" / "26.8.1")
    assert find_libreoffice(tmp_path / "state") == (own, "own")


def test_the_newest_own_version_is_used(tmp_path: Path) -> None:
    _launcher(tmp_path / "libreoffice" / "25.8.7")
    newest = _launcher(tmp_path / "libreoffice" / "26.8.1")
    assert find_libreoffice(tmp_path) == (newest, "own")


def test_a_copy_that_does_not_start_is_found_without_a_version(tmp_path: Path) -> None:
    _launcher(tmp_path / "libreoffice" / "26.8.1", text="not a version line")
    status = libreoffice_status(tmp_path)
    assert status["found"] and status["version"] is None


def test_convert_waits_for_a_launcher_that_returns_before_it_has_written_the_pdf(
    tmp_path: Path,
) -> None:
    """The Windows launcher does: the work finishes in a process it started, after it returned."""
    launcher = tmp_path / "program" / "soffice"
    launcher.parent.mkdir()
    # Arguments: profile, --headless, --convert-to, pdf, --outdir, <dir>, <source>.
    launcher.write_text(
        "#!/bin/sh\n"
        'nohup sh -c \'sleep 0.6; printf "%%PDF-1.7" > "$0/$1.pdf"\' "$6" "check" '
        ">/dev/null 2>&1 &\n"
    )
    launcher.chmod(launcher.stat().st_mode | stat.S_IXUSR)
    source = tmp_path / "check.docx"
    source.write_text("x")
    pdf = lo.convert_to_pdf(launcher, source, tmp_path / "out", tmp_path / "profile", timeout=10)
    assert pdf.read_bytes().startswith(b"%PDF")


def test_convert_gives_up_when_no_pdf_ever_appears(tmp_path: Path) -> None:
    launcher = tmp_path / "program" / "soffice"
    launcher.parent.mkdir()
    launcher.write_text("#!/bin/sh\nexit 0\n")
    launcher.chmod(launcher.stat().st_mode | stat.S_IXUSR)
    source = tmp_path / "check.docx"
    source.write_text("x")
    with pytest.raises(TimeoutError):
        lo.convert_to_pdf(launcher, source, tmp_path / "out", tmp_path / "profile", timeout=1.0)


def _fake_that_writes(tmp_path: Path, pdf: Path) -> Path:
    """A launcher that "converts" by copying a prepared PDF to where LibreOffice would put it."""
    launcher = tmp_path / "libreoffice" / "26.8.1" / "program" / "soffice"
    launcher.parent.mkdir(parents=True)
    # Arguments: profile, --headless, --convert-to, <filter>, --outdir, <dir>, <source>.
    launcher.write_text(f'#!/bin/sh\nname=$(basename "$7"); cp "{pdf}" "$6/${{name%.*}}.pdf"\n')
    launcher.chmod(launcher.stat().st_mode | stat.S_IXUSR)
    return launcher


def test_a_word_file_is_previewed_through_libreoffice_when_no_office_program_is_there(
    tmp_path: Path,
) -> None:
    from PIL import Image

    from coscribe.tools import _thumbnail

    pdf = tmp_path / "made.pdf"
    Image.new("RGB", (200, 300), "white").save(pdf)
    state = tmp_path / "state"
    _fake_that_writes(state, pdf)
    word = tmp_path / "report.docx"
    word.write_bytes(b"not read by the fake")

    name, reason = _thumbnail.render_thumbnail(word, state)

    assert reason is None and name is not None
    assert (state / "previews" / name).is_file()


def test_without_any_office_program_the_reason_names_all_three(tmp_path: Path) -> None:
    from coscribe.tools import _thumbnail

    word = tmp_path / "report.docx"
    word.write_bytes(b"x")

    name, reason = _thumbnail.render_thumbnail(word, tmp_path / "state")

    assert name is None and reason == _thumbnail.NO_OFFICE_PROGRAM
    assert "LibreOffice" in (reason or "")


def test_convert_with_libreoffice_is_none_without_one_and_for_a_format_it_has_no_filter_for(
    tmp_path: Path,
) -> None:
    source = tmp_path / "a.docx"
    source.write_text("x")
    assert lo.convert_with_libreoffice(tmp_path, source, tmp_path / "a.pdf", "pdf", 5) is None
    _launcher(tmp_path / "libreoffice" / "26.8.1")
    assert lo.convert_with_libreoffice(tmp_path, source, tmp_path / "a.rtf", "rtf", 5) is None


def test_convert_with_libreoffice_moves_the_result_to_the_name_asked_for(tmp_path: Path) -> None:
    from PIL import Image

    pdf = tmp_path / "made.pdf"
    Image.new("RGB", (50, 50), "white").save(pdf)
    state = tmp_path / "state"
    _fake_that_writes(state, pdf)
    source = tmp_path / "in" / "report.docx"
    source.parent.mkdir()
    source.write_text("x")
    target = tmp_path / "out" / "renamed.pdf"
    target.parent.mkdir()

    program = lo.convert_with_libreoffice(state, source, target, "pdf", 10)

    assert program == "LibreOffice" and target.is_file()
    assert not (target.parent / "report.pdf").exists()


def test_a_failed_libreoffice_conversion_is_a_value_error_with_a_fixed_text(
    tmp_path: Path,
) -> None:
    state = tmp_path / "state"
    launcher = state / "libreoffice" / "26.8.1" / "program" / "soffice"
    launcher.parent.mkdir(parents=True)
    launcher.write_text("#!/bin/sh\necho /secret/path >&2\nexit 3\n")
    launcher.chmod(launcher.stat().st_mode | stat.S_IXUSR)
    source = tmp_path / "a.docx"
    source.write_text("x")

    with pytest.raises(ValueError, match="could not convert") as caught:
        lo.convert_with_libreoffice(state, source, tmp_path / "a.pdf", "pdf", 5)

    assert "secret" not in str(caught.value)
