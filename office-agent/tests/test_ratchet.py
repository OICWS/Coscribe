"""scripts/ratchet.py: what counts as worse, and that each metric measures what it says."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "ratchet.py"


@pytest.fixture(scope="module")
def ratchet() -> ModuleType:
    spec = importlib.util.spec_from_file_location("ratchet", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["ratchet"] = module
    spec.loader.exec_module(module)
    return module


def test_a_new_name_or_a_bigger_number_is_worse_and_a_smaller_one_is_better(
    ratchet: ModuleType,
) -> None:
    baseline = {"file_lines": {"a.py": 900, "b.py": 1000, "c.py": 850}}
    measured = {"file_lines": {"a.py": 950, "b.py": 900, "d.py": 801}}

    worse, better = ratchet.compare(baseline, measured)

    assert worse == ["file_lines: a.py grew 900 -> 950", "file_lines: new  d.py = 801"]
    assert better == ["file_lines: b.py 1000 -> 900", "file_lines: c.py is gone (was 850)"]


def test_an_unchanged_measurement_is_neither(ratchet: ModuleType) -> None:
    both = {"suppressions": {"noqa": 3}}

    assert ratchet.compare(both, both) == ([], [])


def test_only_files_above_the_limit_are_listed(ratchet: ModuleType, tmp_path: Path) -> None:
    package = tmp_path / "src" / "coscribe"
    package.mkdir(parents=True)
    (package / "big.py").write_text("x = 1\n" * 12, encoding="utf-8")
    (package / "small.py").write_text("x = 1\n" * 3, encoding="utf-8")
    ratchet.ROOT = tmp_path

    sizes = ratchet.file_lines(package, listed=10)

    assert sizes == {"src/coscribe/big.py": 12}


def test_a_long_function_is_named_with_its_class(ratchet: ModuleType, tmp_path: Path) -> None:
    package = tmp_path / "src" / "coscribe"
    package.mkdir(parents=True)
    body = "".join(f"        y{i} = {i}\n" for i in range(8))
    (package / "m.py").write_text(
        f"class A:\n    def long(self):\n{body}\n    def short(self):\n        return 1\n",
        encoding="utf-8",
    )
    ratchet.ROOT = tmp_path

    found = ratchet.long_functions(package, listed=5)

    assert list(found) == ["src/coscribe/m.py::A.long"]


def test_suppressions_are_counted_by_kind(ratchet: ModuleType, tmp_path: Path) -> None:
    package = tmp_path / "src" / "coscribe"
    package.mkdir(parents=True)
    (package / "m.py").write_text(
        "a = 1  # noqa: E501\nb = 2  # type: ignore[x]\nc = 3  # noqa\n", encoding="utf-8"
    )

    assert ratchet.suppressions(package) == {"type_ignore": 1, "noqa": 2, "pragma_no_cover": 0}


def test_deep_and_private_cross_package_imports_are_found_and_own_package_ones_are_not(
    ratchet: ModuleType, tmp_path: Path
) -> None:
    package = tmp_path / "src" / "coscribe"
    for name in ("web", "tools"):
        (package / name).mkdir(parents=True)
        (package / name / "__init__.py").write_text("", encoding="utf-8")
    (package / "tools" / "documents.py").write_text("", encoding="utf-8")
    (package / "tools" / "other.py").write_text(
        "from coscribe.tools.documents import X\n", encoding="utf-8"
    )
    (package / "web" / "app.py").write_text(
        "from coscribe.tools.documents import _helper, Public\nfrom coscribe.tools import Fine\n",
        encoding="utf-8",
    )

    found = ratchet.deep_imports(package)

    assert found == {
        "coscribe.web.app -> coscribe.tools.documents": 1,
        "coscribe.web.app -> coscribe.tools.documents:_helper": 1,
    }


def test_a_test_with_no_assert_is_listed_and_one_with_raises_is_not(
    ratchet: ModuleType, tmp_path: Path
) -> None:
    (tmp_path / "test_a.py").write_text(
        "import pytest\n"
        "def test_crash_only():\n    run()\n"
        "def test_asserts():\n    assert run()\n"
        "def test_raises():\n    with pytest.raises(ValueError):\n        run()\n"
        "def test_mock(m):\n    m.assert_called_once()\n",
        encoding="utf-8",
    )
    ratchet.ROOT = tmp_path

    assert list(ratchet.tests_without_a_check(tmp_path)) == ["test_a.py::test_crash_only"]


def test_patching_a_dotted_name_by_string_is_counted_per_file(
    ratchet: ModuleType, tmp_path: Path
) -> None:
    (tmp_path / "test_a.py").write_text(
        'def test_x(monkeypatch):\n    monkeypatch.setattr("' + "coscribe" + '.x.y", 1)\n'
        '    monkeypatch.setattr(obj, "attr", 1)\n',
        encoding="utf-8",
    )
    ratchet.ROOT = tmp_path

    assert ratchet.patch_by_string(tmp_path) == {"test_a.py": 1}


def test_the_committed_baseline_has_every_metric(ratchet: ModuleType) -> None:
    """Report only for now: the baseline must exist and name every metric, but a number
    that got worse does not fail the tests until the ratchet is enforced."""
    baseline = ratchet.json.loads(ratchet.BASELINE.read_text(encoding="utf-8"))

    assert set(baseline) == set(ratchet.METRICS)
