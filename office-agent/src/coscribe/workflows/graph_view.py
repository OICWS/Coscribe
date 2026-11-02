"""The graph a workflow runs as, the way LangGraph compiles it, for the editor's compiled view:
the same `build_graph` a run uses, with nothing to run against, so what it shows is what runs.
Every node keeps its own name, with the step it belongs to beside it."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..workflow_spec import Workflow, walk
from .engine import StepContext, build_graph

# The engine's nodes besides one per step (`engine._GraphBuilder.wire`).
_INTERNAL = {"next": "Next item", "collect": "Keep this pass"}


def _label(node: str, titles: dict[str, str]) -> str:
    if node in ("__start__", "__end__"):
        return "Start" if node == "__start__" else "Done"
    kind, _, step_id = node.partition("__")
    title = titles.get(step_id, step_id)
    return title if kind == "step" else f"{_INTERNAL.get(kind, kind)} · {title}"


def _text(text: str) -> str:
    return text.replace('"', "#quot;").replace("\n", " ")


def compiled_graph(workflow: Workflow) -> dict[str, Any]:
    """{"nodes": [{"id", "label"}], "edges": [{"source", "target", "conditional", "label"}],
    "mermaid"}; no nodes for a workflow without steps, which doesn't compile."""
    if not workflow.steps:
        return {"nodes": [], "edges": [], "mermaid": ""}
    context = StepContext(
        tools={}, workspace_root=Path(), state_dir=Path(), make_model=lambda _name: None
    )
    graph = build_graph(workflow, context, lambda _record: None, None).get_graph()
    titles = {placed.step.id: placed.step.title for placed in walk(workflow.every_step())}
    nodes = [{"id": node, "label": _label(node, titles)} for node in graph.nodes]
    edges = [
        {
            "source": edge.source,
            "target": edge.target,
            "conditional": edge.conditional,
            "label": str(edge.data) if edge.data is not None else None,
        }
        for edge in graph.edges
    ]
    short = {node["id"]: f"n{index}" for index, node in enumerate(nodes)}
    lines = ["flowchart TD"]
    for node in nodes:
        label, name = _text(node["label"]), _text(node["id"])
        end = node["id"] in ("__start__", "__end__")
        text = f'(["{label}"])' if end else f'["{label}<br/><small>{name}</small>"]'
        lines.append(f"  {short[node['id']]}{text}")
    for edge in edges:
        arrow = "-.->" if edge["conditional"] else "-->"
        label = f'|"{_text(edge["label"])}"|' if edge["label"] else ""
        lines.append(f"  {short[edge['source']]} {arrow}{label} {short[edge['target']]}")
    return {"nodes": nodes, "edges": edges, "mermaid": "\n".join(lines)}
