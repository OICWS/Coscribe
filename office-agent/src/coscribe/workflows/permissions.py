"""What a workflow will touch, worked out from its steps: the sites it
opens, the folders it names, the scripts and other consequential tools it
runs. Shown where the person reviews it -- saving is the consent -- and
what a saved run is held to: a site or folder outside the granted lists
stops the run and waits for an answer.

Only what the steps say outright can be listed. A site or folder that
comes from an input, or that a script decides at run time, isn't known
until then, which is why a run can still stop to ask. An agent step
(decision 0028) says outright what it may touch: its declared folders and
sites are part of what saving allows."""

from __future__ import annotations

import json
import re
from collections.abc import Collection, Mapping
from pathlib import Path, PureWindowsPath
from typing import Any
from urllib.parse import urlparse

from ..workflow_spec import (
    AgentStep,
    LoopStep,
    ScriptStep,
    Step,
    ToolStep,
    Workflow,
    child_lists,
    render_text,
    step_output,
    step_references,
    walk,
)

URL_TOOLS = frozenset({"browser_navigate", "browser_tabs"})
SCRIPT_TOOLS = frozenset({"run_python_script", "run_node_script", "run_background_script"})
_FOLDER_ARGS = (
    "save_to",
    "path",
    "file_path",
    "destination",
    "dest",
    "folder",
    "directory",
    "output_path",
)
# What is worth listing: reading and writing in the workspace is the
# ordinary work of a workflow, and the browser's reach is its sites.
_NOTABLE_RISKS = ("EXEC", "EXTERNAL")


def site_of(url: str) -> str | None:
    """ "https://www.Example.com/a" -> "example.com", as the desktop app
    names a site: a host, without "www.", and a bare domain covers its
    subdomains."""
    text = url.strip().lower()
    if not text:
        return None
    try:
        host = urlparse(text if "://" in text else f"https://{text}").hostname
    except ValueError:
        return None
    if not host:
        return None
    host = host.removeprefix("www.").rstrip(".")
    return host or None


def _is_absolute(text: str) -> bool:
    return Path(text).is_absolute() or PureWindowsPath(text).is_absolute()


def _folder_of(text: str) -> str:
    path = PureWindowsPath(text) if PureWindowsPath(text).drive else Path(text)
    return str(path.parent if path.suffix else path)


def _literal(value: Any, defaults: Mapping[str, Any]) -> str | None:
    """A step argument as text when the steps alone decide it: written out,
    or filled from inputs that have defaults."""
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return render_text(value, dict(defaults))
    except Exception:  # noqa: BLE001 -- an unresolved reference just means "not known yet"
        return None


def granted_by(workflow: Workflow) -> dict[str, list[str]]:
    """The folders and sites the steps themselves name: what saving the
    workflow allows it."""
    defaults = {i.name: i.default for i in workflow.inputs if i.default is not None}
    folders: list[str] = []
    sites: list[str] = []
    for placed in walk(workflow.steps):
        step = placed.step
        if isinstance(step, AgentStep):
            folders += [f for f in step.folders if f not in folders]
            for declared in step.sites:
                site = site_of(declared)
                if site and site not in sites:
                    sites.append(site)
            continue
        if not isinstance(step, ToolStep):
            continue
        if step.tool in URL_TOOLS:
            url = _literal(step.args.get("url"), defaults)
            site = site_of(url) if url else None
            if site and site not in sites:
                sites.append(site)
        for name in _FOLDER_ARGS:
            text = _literal(step.args.get(name), defaults)
            if text and _is_absolute(text):
                folder = _folder_of(text)
                if folder not in folders:
                    folders.append(folder)
    return {"folders": folders, "sites": sites}


def _unknown_sites(workflow: Workflow) -> list[str]:
    """Steps that open a site taken from an input or an earlier step."""
    defaults = {i.name: i.default for i in workflow.inputs if i.default is not None}
    titles: list[str] = []
    for placed in walk(workflow.steps):
        step = placed.step
        if isinstance(step, ToolStep) and step.tool in URL_TOOLS and step.args.get("url"):
            if _literal(step.args.get("url"), defaults) is None:
                titles.append(step.title)
    return titles


def _references_any(step: Step, names: set[str]) -> bool:
    return any(ref.split(".", 1)[0] in names for ref in step_references(step))


def untrusted_agent_steps(workflow: Workflow, outside_tools: Collection[str]) -> list[str]:
    """The agent steps that read what came from outside -- a page, a web
    response, a connector's data -- through their references: they get
    read-only tools unless the person grants more (decision 0028). A value
    is from outside when a step calling one of `outside_tools` made it, or
    a step that read such a value did, a loop's item over it included."""
    tainted: set[str] = set()
    found: list[str] = []

    def visit(steps: list[Step]) -> None:
        for step in steps:
            reads = _references_any(step, tainted)
            if isinstance(step, AgentStep) and reads and not step.trusted_input:
                found.append(step.id)
            makes = step_output(step)
            if isinstance(step, LoopStep) and reads:
                tainted.add(step.item)
            outside = isinstance(step, ToolStep) and step.tool in outside_tools
            # A high or full agent has the environment's tools, the web among them.
            outside = outside or (
                isinstance(step, AgentStep)
                and (step.autonomy != "bounded" or any(t in outside_tools for t in step.tools))
            )
            for _arm, children in child_lists(step):
                visit(children)
            if isinstance(step, LoopStep) and step.collect:
                reads = reads or step.collect.split(".", 1)[0] in tainted
            if makes and (reads or outside):
                tainted.add(makes)

    visit(workflow.steps)
    return found


def _agents(workflow: Workflow, untrusted: list[str]) -> list[dict[str, Any]]:
    return [
        {
            "title": placed.step.title,
            "autonomy": placed.step.autonomy,
            "tools": list(placed.step.tools),
            "folders": list(placed.step.folders),
            "sites": list(placed.step.sites),
            "max_steps": placed.step.max_steps,
            "read_only": placed.step.id in untrusted,
        }
        for placed in walk(workflow.steps)
        if isinstance(placed.step, AgentStep)
    ]


def summarize(
    workflow: Workflow,
    risks: Mapping[str, str],
    granted: Mapping[str, list[str]] | None = None,
    outside_tools: Collection[str] = (),
) -> dict[str, Any]:
    """What the review card shows: the granted folders and sites (what the
    steps name, plus anything allowed since), the steps that run scripts,
    the other tools that do something outside the workspace, the steps
    whose site is only known at run time, and each agent step with what it
    may call and whether it reads outside content."""
    named = granted_by(workflow)
    folders = list(dict.fromkeys([*named["folders"], *((granted or {}).get("folders") or [])]))
    sites = list(dict.fromkeys([*named["sites"], *((granted or {}).get("sites") or [])]))
    scripts: list[str] = []
    notable: list[dict[str, str]] = []
    for placed in walk(workflow.steps):
        step = placed.step
        if isinstance(step, ScriptStep) or (
            isinstance(step, ToolStep) and step.tool in SCRIPT_TOOLS
        ):
            scripts.append(step.title)
        elif (
            isinstance(step, ToolStep)
            and not step.tool.startswith("browser_")
            and risks.get(step.tool) in _NOTABLE_RISKS
        ):
            notable.append({"tool": step.tool, "title": step.title, "risk": risks[step.tool]})
    return {
        "folders": folders,
        "sites": sites,
        "scripts": scripts,
        "notable": notable,
        "sites_at_run_time": _unknown_sites(workflow),
        "agents": _agents(workflow, untrusted_agent_steps(workflow, outside_tools)),
    }


_URL = re.compile(r"https?://[^\s\"'\\<>)]+")
_MAX_SITES = 20


def sites_in(outputs: list[Any]) -> list[str]:
    """The sites a run's step outputs show it opened, in order: the browser
    tools name the page they end on."""
    found: list[str] = []
    for match in _URL.finditer(json.dumps(outputs, ensure_ascii=False, default=str)):
        site = site_of(match.group(0))
        if site and site not in found:
            found.append(site)
            if len(found) == _MAX_SITES:
                break
    return found
