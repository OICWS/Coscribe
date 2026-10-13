"""Property tests for the promise of `WorkspaceScope.resolve`: a path it
accepts lies inside the workspace root or a folder the user allowed for that
use, whatever the text of the path. Hypothesis builds paths out of the pieces
that trick path code: `..`, `.`, empty segments, both separators, absolute
forms, drive letters, `~`, a sibling folder that shares the root's name as a
prefix, and a symlink pointing out.

What a piece means depends on the platform, and the property holds on both:
on Linux a backslash and `C:` are ordinary file-name characters, so those
paths resolve inside the root; on Windows they are separators and a drive, so
they are refused or land where they say. Only the Linux behaviour has been run
here; the nightly Windows job runs the other.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from coscribe.tools._workspace import WorkspaceScope

# `tmp_path` is only read by the examples: `resolve` creates nothing.
_SETTINGS = settings(
    deadline=None,
    derandomize=True,
    max_examples=300,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)


class _Layout:
    def __init__(self, base: Path) -> None:
        self.base = base
        self.root = base / "ws"
        self.readable = base / "readable"
        self.writable = base / "writable"
        for folder in (self.root, self.readable, self.writable, base / "ws2", base / "outside"):
            folder.mkdir()
        try:
            (self.root / "link").symlink_to(base / "outside", target_is_directory=True)
        except OSError:
            pass  # Windows without the privilege: "link" is then a plain missing name.
        self.scope = WorkspaceScope(
            self.root, extra_readable=[self.readable], extra_writable=[self.writable]
        )

    def allowed(self, write: bool) -> list[Path]:
        folders = [self.root, self.writable] + ([] if write else [self.readable])
        return [Path(os.path.realpath(folder)) for folder in folders]


@pytest.fixture
def layout(tmp_path: Path) -> _Layout:
    return _Layout(tmp_path)


def _inside(path: Path, folder: Path) -> bool:
    try:
        return os.path.commonpath([os.path.realpath(path), folder]) == str(folder)
    except ValueError:  # a different drive
        return False


_PIECES = st.sampled_from(
    ["..", ".", "", "a", "b.txt", "ws", "ws2", "outside", "link", "readable", "writable"]
    + ["~", "C:", "c:", "D:", "\\\\server\\share", "...", " ..", ".. ", "a b"]
)
_SEPARATORS = st.sampled_from(["/", "\\", "//", "\\\\", "/\\", "./", "\\.\\"])


@st.composite
def _paths(draw: st.DrawFn, layout: _Layout) -> str:
    start = draw(
        st.sampled_from(
            ["", "/", "\\", "//", str(layout.base), str(layout.root), str(layout.base / "ws2")]
            + [str(layout.readable), str(layout.writable), str(layout.base / "outside")]
            + [str(layout.root) + "/..", str(layout.root) + "\\.."]
        )
    )
    pieces = draw(st.lists(_PIECES, max_size=7))
    out = start
    for piece in pieces:
        out += draw(_SEPARATORS) + piece
    return out


@_SETTINGS
@given(data=st.data(), write=st.booleans())
def test_an_accepted_path_is_inside_an_allowed_folder(
    layout: _Layout, data: st.DataObject, write: bool
) -> None:
    text = data.draw(_paths(layout))
    try:
        resolved = layout.scope.resolve(text, write=write)
    except PermissionError:
        return  # refused, which is always safe
    assert any(_inside(resolved, folder) for folder in layout.allowed(write)), (
        f"{text!r} was accepted as {resolved}"
    )


@_SETTINGS
@given(data=st.data())
def test_a_relative_path_climbing_out_is_refused(layout: _Layout, data: st.DataObject) -> None:
    ups = data.draw(st.integers(min_value=1, max_value=4))
    separator = data.draw(st.sampled_from(["/", "//", "/./"]))
    tail = data.draw(st.sampled_from(["", "x.txt", "ws2/x.txt", "outside/x.txt"]))
    text = separator.join([".."] * ups + [tail])
    # Under the base folder, one `..` from the root lands in the allowed
    # readable or writable sibling only when it names it, which `tail` never does.
    with pytest.raises(PermissionError):
        layout.scope.resolve(text)


@_SETTINGS
@given(data=st.data(), write=st.booleans())
def test_the_symlink_out_of_the_root_is_not_a_way_out(
    layout: _Layout, data: st.DataObject, write: bool
) -> None:
    if not (layout.root / "link").is_symlink():
        pytest.skip("this platform did not allow a symlink here")
    separator = data.draw(st.sampled_from(["/", "//", "/./"]))
    tail = data.draw(st.sampled_from(["", "x.txt", "sub" + separator + "y.txt"]))
    text = "link" + (separator + tail if tail else "")
    with pytest.raises(PermissionError):
        layout.scope.resolve(text, write=write)


@_SETTINGS
@given(data=st.data(), write=st.booleans())
def test_a_path_inside_the_root_is_accepted_where_it_says(
    layout: _Layout, data: st.DataObject, write: bool
) -> None:
    names = data.draw(
        st.lists(st.sampled_from(["a", "b.txt", "c d", ".hidden"]), min_size=1, max_size=4)
    )
    detours = data.draw(st.integers(min_value=0, max_value=3))
    # `x/..` steps cancel out, and a repeated separator or `.` changes nothing.
    text = "/".join(["x/.."] * detours + ["."] + names)
    resolved = layout.scope.resolve(text, write=write)
    assert resolved == layout.root.resolve().joinpath(*names)
