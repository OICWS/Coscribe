"""coscribe's own LibreOffice: download, check, unpack, trim, move into place (decision 0026).

The real unpack is `msiexec /a` and only runs on Windows; here it is replaced by a function that
writes the tree an unpacked MSI leaves, so everything around it is what is tested.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from coscribe.tools import find_libreoffice
from coscribe.tools import libreoffice as lo
from coscribe.tools import libreoffice_install as install


def _tree(root: Path) -> None:
    """The parts of an unpacked LibreOffice that matter to the trim, each a little file."""
    files = [
        "program/soffice.com",
        "program/resource/en-US/a.mo",
        "program/resource/de/a.mo",
        "program/resource/fr/a.mo",
        "share/registry/res/fcfg_langpack_en-US.xcd",
        "share/registry/res/fcfg_langpack_de.xcd",
        "share/registry/main.xcd",
        "share/extensions/dict-en/en.dic",
        "share/extensions/dict-de/de.dic",
        "share/extensions/nlpsolver/x",
        "share/config/images_colibre.zip",
        "share/config/soffice.cfg/writer.ui",
        "share/gallery/g",
        "share/template/t",
        "help/h",
        "readmes/r",
        "Fonts/f.ttf",
        "LibreOffice.msi",
    ]
    for name in files:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("x")


@pytest.fixture(autouse=True)
def _a_windows_computer_with_nothing_installed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(lo.shutil, "which", lambda _name: None)
    monkeypatch.setattr(lo, "_launcher_names", lambda: ("soffice.com",))


@pytest.fixture
def served(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> str:
    """A file standing in for the MSI, pinned the way the real one is, and a fake unpack."""
    package = tmp_path / "served.msi"
    package.write_bytes(b"not really an msi")
    pins = {
        "size": package.stat().st_size,
        "sha256": hashlib.sha256(package.read_bytes()).hexdigest(),
        "url": package.as_uri(),
    }
    monkeypatch.setattr(install, "_PINS", {"win32/amd64": pins})
    monkeypatch.setattr(install, "_platform_key", lambda: "win32/amd64")
    monkeypatch.setattr(install, "_unpack", lambda _package, target: _tree(target))
    monkeypatch.setattr(install, "_check", lambda _folder, _state: None)
    return package.as_uri()


def test_an_install_leaves_a_trimmed_copy_that_is_found(tmp_path: Path, served: str) -> None:
    state = tmp_path / "state"
    steps: list[str] = []
    launcher = install.install_libreoffice(state, step=steps.append)
    folder = install.install_dir(state)
    assert launcher == folder / "program" / "soffice.com"
    assert steps == ["download", "unpack", "trim", "check"]
    assert find_libreoffice(state) == (launcher, "own")
    assert install.installed(state)


def test_the_trim_cuts_other_languages_and_keeps_what_conversion_needs(
    tmp_path: Path, served: str
) -> None:
    install.install_libreoffice(tmp_path)
    folder = install.install_dir(tmp_path)
    kept = {p.relative_to(folder).as_posix() for p in folder.rglob("*") if p.is_file()}
    assert kept == {
        "program/soffice.com",
        "program/resource/en-US/a.mo",
        "share/registry/res/fcfg_langpack_en-US.xcd",
        "share/registry/main.xcd",
        "share/config/soffice.cfg/writer.ui",
        "Fonts/f.ttf",
    }


def test_nothing_is_left_beside_the_copy(tmp_path: Path, served: str) -> None:
    install.install_libreoffice(tmp_path)
    assert [p.name for p in (tmp_path / "libreoffice").iterdir()] == [install.LIBREOFFICE_VERSION]


def test_progress_reaches_the_pinned_size(tmp_path: Path, served: str) -> None:
    seen: list[tuple[int, int]] = []
    install.install_libreoffice(tmp_path, progress=lambda done, total: seen.append((done, total)))
    assert seen[-1][0] == seen[-1][1] > 0


def test_a_file_that_does_not_match_the_pinned_hash_is_not_installed(
    tmp_path: Path, served: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    pins = dict(install._PINS["win32/amd64"], sha256="0" * 64)
    monkeypatch.setattr(install, "_PINS", {"win32/amd64": pins})
    with pytest.raises(install.LibreOfficeUnavailable, match="does not match"):
        install.install_libreoffice(tmp_path)
    assert list((tmp_path / "libreoffice").iterdir()) == []


def test_a_copy_that_fails_its_check_is_not_moved_into_place(
    tmp_path: Path, served: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    def broken(_folder: Path, _state: Path) -> None:
        raise install.LibreOfficeUnavailable("The downloaded LibreOffice did not start.")

    monkeypatch.setattr(install, "_check", broken)
    with pytest.raises(install.LibreOfficeUnavailable, match="did not start"):
        install.install_libreoffice(tmp_path)
    assert not install.installed(tmp_path)
    assert list((tmp_path / "libreoffice").iterdir()) == []


def test_an_older_version_goes_once_the_new_one_is_in(tmp_path: Path, served: str) -> None:
    old = tmp_path / "libreoffice" / "25.8.7"
    _tree(old)
    install.install_libreoffice(tmp_path)
    assert not old.exists()


def test_a_second_install_does_nothing(
    tmp_path: Path, served: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    install.install_libreoffice(tmp_path)

    def no_download(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("downloaded again")

    monkeypatch.setattr(install, "_download", no_download)
    launcher = install.install_libreoffice(tmp_path)
    assert launcher == install.install_dir(tmp_path) / "program" / "soffice.com"


def test_too_little_free_space_is_said_before_anything_is_downloaded(
    tmp_path: Path, served: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    class Usage:
        free = 10 * 1024 * 1024

    monkeypatch.setattr(install.shutil, "disk_usage", lambda _path: Usage)
    with pytest.raises(install.LibreOfficeUnavailable, match="2.2 GB"):
        install.install_libreoffice(tmp_path)


def test_other_computers_are_told_there_is_no_download(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(install, "_platform_key", lambda: "linux/x86_64")
    assert install.libreoffice_offer() is None
    with pytest.raises(install.LibreOfficeUnavailable, match="64-bit Windows"):
        install.install_libreoffice(tmp_path)


def test_the_offer_names_the_sizes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(install, "_platform_key", lambda: "win32/amd64")
    offer = install.libreoffice_offer()
    assert offer is not None
    assert offer["version"] == install.LIBREOFFICE_VERSION
    assert offer["download_bytes"] == 374870016


def test_remove_deletes_every_copy_and_the_profile(tmp_path: Path, served: str) -> None:
    install.install_libreoffice(tmp_path)
    (tmp_path / "libreoffice" / "profile").mkdir()
    install.remove_libreoffice(tmp_path)
    assert not (tmp_path / "libreoffice").exists()
    assert find_libreoffice(tmp_path) is None


def test_the_pinned_download_is_the_one_whose_signature_was_checked() -> None:
    pins = install._PINS["win32/amd64"]
    assert pins["sha256"] == "c6298b10cfa1748bcbedad94c62ce771e240e5021bfd6d7a967cd571b04b5312"
    assert pins["size"] == 374870016
    assert install.LIBREOFFICE_VERSION in str(pins["url"])
