"""Script (Python) and Node package environments."""

from __future__ import annotations

import asyncio
import sys
from datetime import UTC, datetime
from typing import Any

from fastapi import (
    APIRouter,
)

from ....runtime_lg import AuditLog, record_decision
from ....tools import (
    UnisolatedConversations,
    fallbacks_for_platform,
    get_interpreter_override,
    install_node_package,
    isolation_status,
    list_node_packages,
    set_interpreter_override,
    uninstall_node_package,
    working_interpreters,
)
from ....tools import install_python_package as install_package
from ....tools import list_python_packages as list_packages
from ....tools import uninstall_python_package as uninstall_package
from ...schemas import (
    ScriptEnvInterpreterUpdate,
    ScriptEnvPackageInstall,
)
from ...state import AppState


def _isolation_routes(router: APIRouter, state: AppState) -> None:
    """Edit environment > Scripts: whether this machine holds a script to its folders, and a
    conversation's choice to run scripts without isolation where it does not."""
    state_dir = state.settings.state_dir

    async def get_script_isolation() -> dict[str, str]:
        return await asyncio.to_thread(isolation_status, state_dir)

    async def retest_script_isolation() -> dict[str, str]:
        # A few seconds: it starts a script in the container and tries each limit.
        return await asyncio.to_thread(isolation_status, state_dir, run=True)

    async def get_thread_scripts(thread_id: str) -> dict[str, bool]:
        return {"unisolated": UnisolatedConversations(state_dir).allowed(thread_id)}

    async def put_thread_scripts(thread_id: str, payload: dict[str, Any]) -> dict[str, bool]:
        allowed = payload.get("unisolated") is True
        chosen = UnisolatedConversations(state_dir)
        if chosen.allowed(thread_id) != allowed:
            chosen.set(thread_id, allowed, datetime.now(UTC).isoformat())
            record_decision(
                AuditLog(state_dir),
                thread_id=thread_id,
                tool_name="run_scripts_without_isolation",
                arguments={"allowed": allowed},
                decision="approve" if allowed else "reject",
                reason="human",
            )
        return {"unisolated": allowed}

    # Registered by reference rather than decorated, so the dead-code check sees them used.
    router.add_api_route("/api/script-isolation", get_script_isolation, methods=["GET"])
    router.add_api_route("/api/script-isolation/test", retest_script_isolation, methods=["POST"])
    router.add_api_route("/api/threads/{thread_id}/scripts", get_thread_scripts, methods=["GET"])
    router.add_api_route("/api/threads/{thread_id}/scripts", put_thread_scripts, methods=["PUT"])


def router(state: AppState) -> APIRouter:
    router = APIRouter()
    settings = state.settings
    _isolation_routes(router, state)

    # Every handler below wraps its real work in asyncio.to_thread --
    # list_packages/install_package/uninstall_package/set_interpreter_override
    # all shell out via subprocess.run with multi-minute timeouts (venv
    # creation alone allows 120s, baseline package seeding 300s -- see
    # tools/exec/script_env.py's _VENV_TIMEOUT/_SETUP_TIMEOUT). Calling them
    # directly from an `async def` route handler, as this code did before,
    # runs that blocking subprocess wait *on the single asyncio event
    # loop* -- not just stalling this one HTTP response, but freezing
    # every other request this whole process serves for as long as pip
    # takes: other REST calls (Settings' other tabs all "went empty"),
    # the WebSocket chat loop (a sent message got no response at all,
    # looking exactly like a dropped connection), everything. Real,
    # live-reported bug: setting a new interpreter override (which
    # deletes the existing script-env venv, see set_interpreter_override's
    # docstring) followed by an Add-package click rebuilt the venv from
    # scratch and reseeded 5 baseline packages over the network -- a
    # multi-minute stretch during which the whole app looked dead. This
    # bug already existed before the interpreter picker (any first-ever
    # venv creation hit it too), just rarely enough to go unnoticed; the
    # picker's rebuild-on-change behavior made it easy to trigger on
    # purpose and land squarely in the recovery flow meant to fix a
    # broken setup.
    @router.get("/api/script-env/packages")
    async def get_script_env_packages() -> list[dict[str, str]]:
        return await asyncio.to_thread(list_packages, settings.state_dir)

    @router.post("/api/script-env/packages")
    async def add_script_env_package(payload: ScriptEnvPackageInstall) -> dict[str, object]:
        name = payload.package.strip()
        if not name:
            return {"success": False, "error": "Package name cannot be blank."}
        return await asyncio.to_thread(install_package, settings.state_dir, name)

    @router.delete("/api/script-env/packages/{name}")
    async def remove_script_env_package(name: str) -> dict[str, object]:
        return await asyncio.to_thread(uninstall_package, settings.state_dir, name)

    @router.get("/api/script-env/interpreter")
    async def get_script_env_interpreter() -> dict[str, object]:
        """What ensure_script_env would try, in order, right now -- the
        Environment tab's manual override (if any) is already reflected
        first in `candidates` since the override changes what
        auto-detection itself returns; `auto_detected` is the plain
        fallback list on its own, filtered to candidates that actually
        run (see working_interpreters' docstring for why sys.executable
        specifically needs this on a packaged build) so the UI never
        offers a chip that's guaranteed to fail validation if clicked."""
        override = get_interpreter_override(settings.state_dir)
        candidates = [sys.executable, *fallbacks_for_platform()]
        return {
            "configured": override,
            "auto_detected": await asyncio.to_thread(working_interpreters, candidates),
        }

    @router.post("/api/script-env/interpreter")
    async def set_script_env_interpreter(payload: ScriptEnvInterpreterUpdate) -> dict[str, object]:
        return await asyncio.to_thread(
            set_interpreter_override, settings.state_dir, payload.path.strip() or None
        )

    # Mirrors the script-env endpoints above exactly, backed by
    # tools/exec/node_env.py's npm-based node-env directory instead -- see that
    # module's docstring for why Node needs a different isolation
    # mechanism than the Python venv, and why node/npm being genuinely
    # optional (unlike Python, coscribe's own runtime) means these can
    # raise where the Python ones effectively never do in practice. Same
    # asyncio.to_thread reasoning as the script-env handlers above.
    @router.get("/api/node-env/packages")
    async def get_node_env_packages() -> list[dict[str, str]]:
        return await asyncio.to_thread(list_node_packages, settings.state_dir)

    @router.post("/api/node-env/packages")
    async def add_node_env_package(payload: ScriptEnvPackageInstall) -> dict[str, object]:
        name = payload.package.strip()
        if not name:
            return {"success": False, "error": "Package name cannot be blank."}
        return await asyncio.to_thread(install_node_package, settings.state_dir, name)

    @router.delete("/api/node-env/packages/{name}")
    async def remove_node_env_package(name: str) -> dict[str, object]:
        return await asyncio.to_thread(uninstall_node_package, settings.state_dir, name)

    return router
