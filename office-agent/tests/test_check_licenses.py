from scripts.check_licenses import strong_copyleft


def _pkg(licence: str) -> list[dict[str, str]]:
    return [{"Name": "dep", "Version": "1.0", "License": licence}]


def test_gpl_agpl_and_sspl_are_flagged() -> None:
    for licence in (
        "GPL-3.0-only",
        "GNU General Public License v3 (GPLv3)",
        "GNU Affero General Public License v3",
        "AGPL-3.0",
        "SSPL-1.0",
    ):
        assert strong_copyleft(_pkg(licence)), licence


def test_permissive_and_weak_copyleft_pass() -> None:
    for licence in (
        "MIT",
        "Apache-2.0",
        "BSD-3-Clause",
        "MPL-2.0",
        "LGPL-3.0-or-later",
        "GNU Lesser General Public License v3 (LGPLv3)",
        "GNU Library or Lesser General Public License (LGPL)",
    ):
        assert not strong_copyleft(_pkg(licence)), licence


def test_a_dual_licence_with_a_permissive_option_passes() -> None:
    assert not strong_copyleft(_pkg("GPL-2.0-only OR MIT"))
    assert strong_copyleft(_pkg("GPL-2.0-only OR GPL-3.0-only"))
