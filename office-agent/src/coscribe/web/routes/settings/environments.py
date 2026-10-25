"""Settings › Capabilities: scripts (isolation, Python, packages) and commands."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from fastapi import (
    APIRouter,
)
from fastapi.responses import JSONResponse

from ....code_runtime import CodexUnavailable, code_service
from ....runtime_lg import AuditLog, record_decision
from ....tools import (
    Capabilities,
    ensure_own_python,
    find_pythons,
    get_interpreter_override,
    install_node_package,
    isolation_status,
    list_node_packages,
    own_python_offer,
    record_sandbox_setup,
    release_private_folders,
    run_as_administrator,
    sandbox_codex,
    sandbox_mode,
    sandbox_setup_argv,
    sandbox_status,
    sandbox_uninstall_argv,
    set_interpreter_override,
    uninstall_node_package,
    warm_up_sandbox,
)
from ....tools import install_python_package as install_package
from ....tools import list_python_packages as list_packages
from ....tools import uninstall_python_package as uninstall_package
from ...schemas import (
    CommandSandboxSetup,
    ScriptEnvInterpreterUpdate,
    ScriptEnvPackageInstall,
)
from ...state import AppState


def _isolation_routes(router: APIRouter, state: AppState) -> None:
    """Settings › Capabilities: whether this machine holds a script to its folders."""
    state_dir = state.settings.state_dir

    async def get_script_isolation() -> dict[str, str]:
        return await asyncio.to_thread(isolation_status, state_dir)

    async def retest_script_isolation() -> dict[str, str]:
        # A few seconds: it starts a script in the container and tries each limit.
        return await asyncio.to_thread(isolation_status, state_dir, run=True)

    # Registered by reference rather than decorated, so the dead-code check sees them used.
    router.add_api_route("/api/script-isolation", get_script_isolation, methods=["GET"])
    router.add_api_route("/api/script-isolation/test", retest_script_isolation, methods=["POST"])


def _capability_routes(router: APIRouter, state: AppState) -> None:
    """Settings › Capabilities: whether scripts and commands may run on this computer."""
    state_dir = state.settings.state_dir

    async def get_capabilities() -> dict[str, bool]:
        return Capabilities(state_dir).get()

    async def put_capability(name: str, payload: dict[str, Any]) -> Any:
        capabilities = Capabilities(state_dir)
        current = capabilities.get()
        if name not in current:
            return JSONResponse({"error": f"No capability {name!r}"}, status_code=404)
        on = payload.get("on") is True
        changed = current[name] != on
        if changed:
            current = capabilities.set(name, on)
        left: list[str] = []
        if name == "commands_hide_private_folders" and not on:
            # Codex leaves some of its deny entries behind (#601); also when already off, so
            # turning it off again retries what was left.
            left = await asyncio.to_thread(release_private_folders, state_dir)
        if changed or left:
            # What coscribe may run is a security setting: kept like an approval.
            record_decision(
                AuditLog(state_dir),
                thread_id="",
                tool_name=f"capability_{name}",
                arguments={"on": on, **({"not_cleared": left} if left else {})},
                decision="approve" if on else "reject",
                reason="human",
            )
        if left:
            return JSONResponse(
                {"error": "Turned off, but these folders still hide from commands: "
                 + ", ".join(left) + ". Turning it off again retries."},
                status_code=500,
            )  # fmt: skip
        return current

    async def get_folders() -> dict[str, str]:
        """Where what this page downloads lives, so the person can find it."""
        return {
            "codex": str(Path(state_dir) / "codex"),
            "python_packages": str(Path(state_dir) / "script-env"),
            "node_packages": str(Path(state_dir) / "node-env"),
        }

    router.add_api_route("/api/capabilities", get_capabilities, methods=["GET"])
    router.add_api_route("/api/capabilities/folders", get_folders, methods=["GET"])
    router.add_api_route("/api/capabilities/{name}", put_capability, methods=["PUT"])


_SANDBOX_SETUP_SECONDS = 600


def _sandbox_routes(router: APIRouter, state: AppState) -> None:
    """Settings › Capabilities: the command sandbox (decision 0022), set up once by an
    administrator and removed from here."""
    state_dir = state.settings.state_dir

    def audit(action: str, error: str) -> None:
        record_decision(
            AuditLog(state_dir),
            thread_id="",
            tool_name=f"command_sandbox_{action}",
            arguments={"error": error} if error else {},
            decision="reject" if error else "approve",
            reason="human",
        )

    # The step setup or removal is on, so the row can say what it waits for. Setup: "download"
    # (Codex, with its progress), "approve" (the administrator prompt, then Codex's setup) or
    # "check"; removal: "release" (the private folders' permissions) or "uninstall".
    step = {"now": "", "mode": ""}

    async def get_sandbox() -> dict[str, Any]:
        if step["now"]:
            progress = code_service(state.settings).status()["progress"]
            return {
                "state": "working",
                "detail": step["now"],
                "progress": progress,
                "mode": step["mode"],
            }
        return sandbox_status(state_dir)

    async def set_up_sandbox(body: CommandSandboxSetup | None = None) -> dict[str, Any]:
        mode = body.mode if body else "elevated"
        if sandbox_status(state_dir)["state"] == "unsupported" or step["now"]:
            return await get_sandbox()
        try:
            step["now"], step["mode"] = "download", mode
            try:
                codex = await code_service(state.settings).download()
            except CodexUnavailable as exc:
                error = exc.args[0] if exc.args else "Codex couldn't be downloaded."
                record_sandbox_setup(state_dir, None, error, mode)
                audit("setup", error)
                return sandbox_status(state_dir)
            error = ""
            if mode == "elevated":
                step["now"] = "approve"
                error = await asyncio.to_thread(
                    run_as_administrator,
                    sandbox_setup_argv(codex, state_dir),
                    state_dir,
                    _SANDBOX_SETUP_SECONDS,
                )
            record_sandbox_setup(state_dir, None if error else codex, error, mode)
            if not error:
                step["now"] = "check"
                tried = await asyncio.to_thread(warm_up_sandbox, state_dir)
                # Elevated setup proved itself; without it, the test command is the only proof.
                if tried and mode == "unelevated":
                    error = f"A test command didn't run in it: {tried}"
                    record_sandbox_setup(state_dir, None, error, mode)
            audit(f"setup_{mode}" if mode == "unelevated" else "setup", error)
            return sandbox_status(state_dir)
        finally:
            step["now"] = ""

    async def remove_sandbox() -> dict[str, Any]:
        if step["now"]:
            return await get_sandbox()
        codex = sandbox_codex(state_dir)
        try:
            # First, while the group still exists so its entries can be named; also when this
            # Codex is gone, since the entries outlive it. icacls walks each folder, which takes a
            # while before the administrator prompt, so the row says so.
            step["now"], step["mode"] = "release", sandbox_mode(state_dir)
            left = await asyncio.to_thread(release_private_folders, state_dir)
            error = ""
            if left:
                error = "Some folders still hide from commands: " + ", ".join(left)
            elif codex is not None and sandbox_mode(state_dir) == "elevated":
                # Only the elevated mode made users and firewall rules to take away.
                step["now"] = "uninstall"
                error = await asyncio.to_thread(
                    run_as_administrator,
                    sandbox_uninstall_argv(codex),
                    state_dir,
                    _SANDBOX_SETUP_SECONDS,
                )
            record_sandbox_setup(state_dir, codex if error else None, mode=sandbox_mode(state_dir))
            audit("uninstall", error)
            return {**sandbox_status(state_dir), "error": error}
        finally:
            step["now"] = ""

    router.add_api_route("/api/command-sandbox", get_sandbox, methods=["GET"])
    router.add_api_route("/api/command-sandbox", set_up_sandbox, methods=["POST"])
    router.add_api_route("/api/command-sandbox", remove_sandbox, methods=["DELETE"])


def router(state: AppState) -> APIRouter:
    router = APIRouter()
    settings = state.settings
    _isolation_routes(router, state)
    _capability_routes(router, state)
    _sandbox_routes(router, state)

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
        """The chosen interpreter (None: the first one found), every Python 3 on this computer
        that runs, and coscribe's own Python on offer (#586)."""
        state_dir = settings.state_dir
        return {
            "configured": get_interpreter_override(state_dir),
            "found": await asyncio.to_thread(find_pythons, state_dir),
            "own_python": own_python_offer(state_dir),
        }

    async def download_own_python() -> dict[str, object]:
        """Downloads coscribe's own Python (about 30 MB) and chooses it; only ever on request."""
        try:
            python = await asyncio.to_thread(ensure_own_python, settings.state_dir)
        except RuntimeError as exc:
            return {"success": False, "error": str(exc)}
        if python is None:
            return {"success": False, "error": "coscribe's own Python is only offered on Windows."}
        chosen = await asyncio.to_thread(set_interpreter_override, settings.state_dir, str(python))
        return {**chosen, "path": str(python)}

    # Registered by reference rather than decorated, so the dead-code check sees it used.
    router.add_api_route("/api/script-env/own-python", download_own_python, methods=["POST"])

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
