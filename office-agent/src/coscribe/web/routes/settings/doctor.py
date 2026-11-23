"""/doctor: read-only checks of what coscribe needs on this computer, each with the step that
fixes a problem. Every check asks the same function the feature itself uses to find what it
needs, so a check cannot drift from the feature; `docs/doc-map.toml` lists this file against
those functions' modules, so a change to them asks for this file to be looked at."""

from __future__ import annotations

import asyncio
import logging
import shutil
import sys
from collections.abc import Awaitable, Callable
from typing import Any, Literal, TypedDict

from fastapi import APIRouter
from langchain_core.messages import HumanMessage

from ....config import Settings
from ....conversation import find_browser
from ....runtime import load_custom_providers
from ....runtime_lg import resolve_chat_model
from ....tools import (
    find_pythons,
    isolation_status,
    libreoffice_status,
    own_python_offer,
    sandbox_status,
    venv_python,
)
from ...browser_panel import find_browser_executable
from ...state import AppState

logger = logging.getLogger(__name__)

State = Literal["ok", "problem", "off"]
# A Settings page the fix is on, by the id the Settings window opens it with.
Page = Literal["providers", "capabilities", "workspace"]

_MODEL_SECONDS = 30.0


class Check(TypedDict):
    id: str
    name: str
    state: State
    detail: str
    fix: str
    page: Page | None


def _check(
    id: str, name: str, state: State, detail: str, fix: str = "", page: Page | None = None
) -> Check:
    return {"id": id, "name": name, "state": state, "detail": detail, "fix": fix, "page": page}


async def check_model(settings: Settings) -> Check:
    """One short request to the default model: the key, the address and the model name."""
    name = "Model"
    model_id = settings.default_model
    path = settings.providers_config_path
    custom = load_custom_providers(path) if path is not None else {}
    try:
        model = resolve_chat_model(model_id, custom)
        await asyncio.wait_for(
            model.ainvoke([HumanMessage("Reply with the word OK.")]), _MODEL_SECONDS
        )
    except TimeoutError:
        detail = f"{model_id} did not answer within {int(_MODEL_SECONDS)} seconds."
        fix = "Check the network or proxy, or try again later."
        return _check("model", name, "problem", detail, fix, "providers")
    except Exception as exc:  # any provider error is the finding itself
        detail = f"{model_id}: {str(exc)[:300]}"
        fix = "Check the provider's key, address and model name."
        return _check("model", name, "problem", detail, fix, "providers")
    return _check("model", name, "ok", f"{model_id} answered.")


def check_python(settings: Settings) -> Check:
    """The Python scripts run on: their environment, or a Python to make it from."""
    name = "Python for scripts"
    script_python = venv_python(settings.state_dir / "script-env")
    if script_python.is_file() and not (settings.state_dir / "script-env.initializing").exists():
        return _check("python", name, "ok", "The scripts' environment is ready.")
    found = find_pythons(settings.state_dir)
    if found:
        detail = f"Python {found[0]['version']} found; scripts set it up on first use."
        return _check("python", name, "ok", detail)
    if own_python_offer(settings.state_dir)["available"]:
        fix = "Download coscribe's own Python."
        return _check("python", name, "problem", "No Python found.", fix, "capabilities")
    return _check("python", name, "problem", "No Python found.", "Install Python 3.11 or later.")


def check_node(settings: Settings) -> Check:
    name = "Node.js for scripts"
    # What node_env's own check asks for before a Node script runs.
    missing = [tool for tool in ("node", "npm") if shutil.which(tool) is None]
    if not missing:
        return _check("node", name, "ok", "node and npm found.")
    detail = f"{' and '.join(missing)} not found."
    return _check("node", name, "problem", detail, "Install Node.js from nodejs.org.")


def check_office_conversion(settings: Settings) -> Check:
    """PDF export and the pictures of documents and decks: the Windows office program converts
    first, LibreOffice when there is none (decision 0012)."""
    name = "Office conversion"
    status = libreoffice_status(settings.state_dir)
    if status["office"]:
        return _check("conversion", name, "ok", f"{status['office']} converts documents.")
    if status["found"] and status["version"]:
        return _check(
            "conversion", name, "ok", f"LibreOffice {status['version']} converts documents."
        )
    if status["found"]:
        detail = f"No Microsoft Office; LibreOffice at {status['path']} does not start."
        fix = "Install Microsoft Office, or download coscribe's own LibreOffice."
        return _check("conversion", name, "problem", detail, fix, "capabilities")
    detail = "Neither Microsoft Office nor LibreOffice found."
    fix = "Install Microsoft Office, or download LibreOffice."
    return _check("conversion", name, "problem", detail, fix, "capabilities")


def check_browser(settings: Settings) -> Check:
    """Edge or Chrome: the browser panel opens pages in it and page pictures are drawn with it."""
    name = "Browser"
    pictures = find_browser()
    # The browser panel's lookup is Windows-only, as the desktop app is.
    panel = find_browser_executable() if sys.platform == "win32" else pictures
    if panel and pictures:
        return _check("browser", name, "ok", "Edge or Chrome found.")
    if pictures:
        detail = "Page pictures work; the browser panel finds no Edge or Chrome."
    else:
        detail = "No Edge or Chrome found."
    return _check("browser", name, "problem", detail, "Install Microsoft Edge or Google Chrome.")


def check_script_isolation(settings: Settings) -> Check:
    """The container scripts run in (decision 0021): read from the last self-test, not rerun."""
    name = "Script isolation"
    status = isolation_status(settings.state_dir)
    state = status["state"]
    if state == "passed":
        return _check("isolation", name, "ok", "Scripts run in their container.")
    if state == "unsupported":
        return _check("isolation", name, "off", "Windows only; scripts run as you.")
    if state == "untested":
        detail = "Not tested yet; it runs before the first script."
        return _check(
            "isolation",
            name,
            "off",
            detail,
            "Run the test in the workspace's settings.",
            "workspace",
        )
    detail = status["failed"] or status["detail"] or "The self-test failed."
    fix = "Scripts are off until the test passes; run it again in the workspace's settings."
    return _check("isolation", name, "problem", detail, fix, "workspace")


def check_command_sandbox(settings: Settings) -> Check:
    """Codex's sandbox for command lines (decision 0022)."""
    name = "Command sandbox"
    status = sandbox_status(settings.state_dir)
    state = status["state"]
    if state == "ready":
        return _check("sandbox", name, "ok", "Commands run in the sandbox.")
    if state == "unsupported":
        return _check("sandbox", name, "off", status["detail"])
    if state == "off":
        detail = "Not set up; each command runs as you, after you approve it."
        return _check("sandbox", name, "off", detail, "Set it up.", "capabilities")
    detail = status["detail"] or "The setup failed."
    return _check("sandbox", name, "problem", detail, "Set it up again.", "capabilities")


LocalCheck = Callable[[Settings], Check]
# The order the card lists them in when all pass; a test runs each one.
LOCAL_CHECKS: tuple[LocalCheck, ...] = (
    check_python,
    check_node,
    check_office_conversion,
    check_browser,
    check_script_isolation,
    check_command_sandbox,
)


async def _local(check: LocalCheck, settings: Settings) -> Check:
    try:
        return await asyncio.to_thread(check, settings)
    except Exception as exc:  # one broken check must not hide the others
        logger.exception("doctor check %s failed", check.__name__)
        name = check.__name__.removeprefix("check_").replace("_", " ").capitalize()
        return _check(check.__name__, name, "problem", f"The check itself failed: {exc}")


async def run_checks(settings: Settings) -> list[Check]:
    pending: list[Awaitable[Check]] = [check_model(settings)]
    pending += [_local(check, settings) for check in LOCAL_CHECKS]
    return list(await asyncio.gather(*pending))


def router(state: AppState) -> APIRouter:
    router = APIRouter()

    # POST, not GET: it spends a model request.
    @router.post("/api/doctor")
    async def doctor() -> dict[str, Any]:
        return {"checks": await run_checks(state.settings)}

    return router
