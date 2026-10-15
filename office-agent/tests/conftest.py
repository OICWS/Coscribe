from collections.abc import Iterator

import pytest

from coscribe.tools import presentations
from coscribe.tools.office.xlsx import helpers as spreadsheets

# The flaky-test policy (tests/flaky_policy.py): the hooks and the quarantine fixture
# register by being names in this module.
from .flaky_policy import (  # noqa: F401
    _quarantine,
    pytest_collection_modifyitems,
    pytest_runtest_logreport,
    pytest_terminal_summary,
)


@pytest.fixture(autouse=True)
def _fast_libreoffice_by_default(
    request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch
) -> None:
    """write_pptx/fill_pptx_template/add_pptx_chart's overflow-QA step and
    write_xlsx's formula-recalculation step each unconditionally shell out
    to a real headless LibreOffice process, regardless of whether the test
    calling them cares about that step at all. That's correct behavior for
    the small number of tests marked `real_libreoffice` (they exist
    specifically to verify real LibreOffice conversion), but once soffice
    is actually installed and working (as it now is in this environment --
    see the SessionStart hook), it turns every ordinary content/geometry
    test that happens to call write_pptx/write_xlsx into a real, slow
    LibreOffice subprocess launch too, which is most of this suite.

    Short-circuits both to their already-well-tested "soffice unavailable"
    branch by default. A test that genuinely needs the real behavior opts
    back in with `@pytest.mark.real_libreoffice`, which still skips
    cleanly (via that file's own `_libreoffice_actually_works()`-style
    probe) in an environment where soffice isn't actually usable.
    """
    if request.node.get_closest_marker("real_libreoffice") is not None:
        return
    monkeypatch.setattr(presentations, "_render_to_pdf", lambda pptx_path: None)
    monkeypatch.setattr(
        spreadsheets,
        "_recalc_xlsx",
        lambda file_path, timeout=None: {
            "status": "skipped",
            "skipped_reason": "disabled in the test suite for speed -- see tests/conftest.py",
        },
    )


@pytest.fixture(autouse=True)
def _manual_permission_mode_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    """Most tests script the model's exact replies, and Auto mode (the
    shipped default) adds a reviewer call before each gated action. Tests
    of the default itself override this."""
    monkeypatch.setenv("COSCRIBE_DEFAULT_PERMISSION_MODE", "manual")


@pytest.fixture(autouse=True)
def _check_chat_websocket_payloads(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Every payload the server sends on a chat WebSocket must match
    conversation/wire.py, so a test run is also a conformance run. The browser
    panel's socket speaks its own protocol and is left alone."""
    from starlette.websockets import WebSocket

    from .wire_check import check_event, violations

    violations.clear()
    original = WebSocket.send_json

    async def checked(self: WebSocket, data: object, mode: str = "text") -> None:
        if self.url.path != "/ws/browser":
            check_event(data)
        await original(self, data, mode)

    monkeypatch.setattr(WebSocket, "send_json", checked)
    yield
    assert not violations, violations
