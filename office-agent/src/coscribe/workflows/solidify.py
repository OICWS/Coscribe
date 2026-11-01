"""Draft a workflow from a conversation that already did the task once.

The conversation is the evidence: every tool call that worked, with its
real arguments and what came back. A curator model turns that into a
workflow spec, which is checked here the same way a saved one is -- plus
against the tools that actually exist -- and sent back with the problems
when it doesn't hold up. The person reviews the draft in the step editor
before anything is saved, so this only has to be a good first pass."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.constants import TAG_NOSTREAM
from pydantic import ValidationError

from ..workflow_spec import (
    AgentStep,
    LLMStep,
    LoopStep,
    ToolStep,
    Workflow,
    parse_workflow,
    raw_child_lists,
    step_references,
    walk,
    workflow_error,
)
from .catalog import describe_params, tool_description
from .engine import UNAVAILABLE_TOOLS

SCRIPT_TOOL = "run_python_script"
# What a run_node_script tool step holds: the call's own result, not what the script printed.
_NODE_RESULT = frozenset({"exit_code", "stdout", "stderr", "timed_out"})
# A bounded agent step may call only its listed tools (decision 0028), so one drafted without
# these stopped a run to ask before looking at a file in its own workspace.
READ_TOOLS = ("list_files", "get_file_info", "read_file")
MAX_ATTEMPTS = 3
_ARGS_CHARS = 4000
_RESULT_CHARS = 600
_TEXT_CHARS = 1500
_TRANSCRIPT_CHARS = 60_000

STEP_FORMAT = """\
Inputs -- values that change from run to run (usually file paths, dates, \
names): {"name": "pdf_path", "label": "PDF to audit", "type": "text" | \
"number" | "date" | "choice" | "yes_no" | "file" | "folder", "default": \
<the value used in the conversation>}. A "date" is "YYYY-MM-DD"; when the \
conversation meant a day relative to when it runs, its default is one of \
"today", "yesterday", "week_start", "last_week_start", "last_week_end", \
"month_start", "last_month_start", "last_month_end", "year_start", worked \
out each run. A "choice" lists its "options"; a "yes_no" defaults to true \
or false and the steps get true or false. Add "required": false only for \
an input that may be left blank at run time -- the steps then get "" and \
must handle it.

Steps -- every step has "id" (lowercase identifier, unique) and "title" \
(short, plain language), plus one "kind":
- "tool": {"tool": "<tool name>", "args": {...}, "save_as": "<name>"} -- \
calls one tool. Copy the arguments of the call that worked exactly, \
replacing only the values that became inputs or come from earlier steps. \
Add "irreversible": true to a step that submits, sends, pays or deletes \
something outside this machine -- a form's final submit, a sent message, \
a payment -- never to one that only moves on, saves a draft or reads. A \
test run stops before such a step, so checking the workflow sends nothing. \
A run_node_script step's save_as holds {"stdout", "stderr", "exit_code"}, \
not what the script printed: a script that finds something wrong throws, \
which stops the run.
- "script": {"code": "<python>", "inputs": {"pdf": "{{pdf_path}}"}, \
"save_as": "<name>"} -- for a run_python_script call. The code reads \
values from a ready-made `inputs` dict (never paste them into the code) \
and must print its result as JSON on its last line, e.g. \
print(json.dumps({"total": total})) -- its save_as then holds that object, \
read as {{name.total}}.
- "llm": {"prompt": "<text with {{references}}>", "fields": [{"name": \
"...", "type": "text" | "number" | "boolean" | "list", "description": \
"..."}], "save_as": "<name>"} -- one model call with no tools, for the \
places where the assistant judged, summarized or classified something. It \
must return exactly those fields, and its save_as holds them as an object: \
read one as {{name.field}}, never {{name}} where you mean the field.
- "check": {"conditions": [{"left": <operand>, "op": "eq" | "ne" | "gt" | \
"ge" | "lt" | "le" | "contains" | "not_contains" | "starts_with" | \
"ends_with" | "empty" | "not_empty" | "before" | "after", "right": \
<operand>}], "match": "all" | "any"} -- stops the run unless every \
condition holds ("all", the default) or one does ("any"). An operand is \
exactly one of {"ref": "name.field"}, {"count": "name"} (length of a list \
or text) or {"value": <literal>}; "empty" and "not_empty" have no "right"; \
"before" and "after" compare dates. A list of conditions is checked in \
order and stops once the answer is known, so a later one may read what an \
earlier one rules out.
- "approval": {"message": "<text with {{references}}>", "when": \
[<condition>, ...], "match": "all" | "any"} -- pauses for a person, only \
when "when" holds if it lists any. Use one before a step that overwrites \
or sends something, only if the conversation asked for a confirmation \
there.

- "loop": {"over": "<name of a list>", "item": "<name for each item>", \
"steps": [...], "collect": "<a name made inside>", "save_as": "<name>", \
"max_items": 50} -- runs its steps once per item, in order. Use it when the \
conversation made the same calls once per item of a list (each file, each \
row) instead of copying every call. The list must come from an input or an \
earlier step. collect/save_as (both or neither) keep one value per item as \
a list -- collect the exact value later steps use (summary.text, not the \
whole summary object); names made inside a loop can't be read after it. \
"until": [<condition>, ...] ends it early once they hold after a pass \
(they may read the item and that pass's results), keeping what it \
collected; use it when the conversation stopped at the first match.
- "branch": {"conditions": [<condition>, ...], "match": "all" | "any", \
"then": [...], "otherwise": [...]} -- only where what the conversation \
did depended on something a run can check.
- "choice": {"value": "<name>", "cases": [{"is": "<value>", "steps": \
[...]}], "otherwise": [...]} -- one of several paths by a value (a \
department, a status): the first case it equals as text, ignoring case, \
else "otherwise". After a branch or a choice, a name can be read only if \
every path makes it.

References: "{{name}}" or "{{name.field}}" reads an input or an earlier \
step's save_as. A whole-string reference keeps the value's type; inside \
longer text it becomes text. A step can only read what comes before it. \
There are no expressions: no counts, filters or formatting inside {{ }}. \
When a prompt needs a number worked out, compute it in a script step first.

Rules:
- Use only the tools listed below, with only the parameters they take.
- Keep the calls that did the work. Leave out exploration (listing, \
peeking, reading the same thing again), failed attempts and anything \
undone later.
- Add a check wherever the conversation verified something (counts that \
must match, a value that must not be empty), grounded in what it found.
- A script that reads a file of this run must stop rather than guess when \
the file is not as it was in the conversation: check that the columns it \
uses are there, raise on a blank value a result needs (never read it as 0 \
or ""), and raise on a row it cannot place -- a value it never saw (a new \
status, an unknown category), an incoming payment that matches no record \
-- unless the conversation showed such rows are left out, and then print \
how many it left out. Incoming money that names no record it can find is \
such a row, not a fee to skip. Match by what identifies a row (an id \
anywhere in a text, written with or without its separators and leading \
zeros; an amount and a date), not by the exact wording the conversation \
saw. Decode text strictly: a file that is not in the expected encoding \
raises instead of turning letters into replacement characters. A wrong \
report that looks finished is worse than a run that stops.
- Keep it as short as the task allows; the reviewer can add steps later.
- Browser steps must work on a fresh page load. Element refs like "e42" \
are numbered afresh on every load, so a step names its element the way the \
page snapshot printed it -- the conversation's calls already show it so, e.g. \
"ref": "checkbox \\"All items\\"" -- and never as a bare ref. Such a step \
waits for its element to appear, so leave out snapshot calls that only \
looked at the page. Navigate by URL. Where the page took long (a report, \
an export), keep a browser_wait_for step and give it a timeout well above \
what the conversation needed, for a slow day. A downloaded file's name \
changes from run to run: read it from the download wait's result, \
{{<its save_as>.file}}, never from the name the conversation saw. Give \
a workflow that downloads files an input for the folder to keep them in \
(default: the folder the user named in the conversation, else \
"downloads") and pass it to the download wait as save_to.
- "notes" lists what you weren't sure about: guesses, values you turned \
into inputs, steps you dropped on purpose.
"""

CURATOR_INSTRUCTIONS = (
    """\
You turn a conversation in which an assistant did a task with tools into a \
workflow: a fixed list of steps that repeats the same task without an \
assistant deciding anything along the way. Reply with one JSON object and \
nothing else:

{"name": "<a few plain words, e.g. Monthly PDF error audit>", \
"workflow": {"version": 1, "inputs": [...], "steps": [...]}, \
"notes": ["<one line per thing the reviewer should check>"]}

If the conversation holds no repeatable task, reply {"error": "<why>"} instead.

"""
    + STEP_FORMAT
)

REVISER_INSTRUCTIONS = (
    """\
You change a saved workflow -- a fixed list of steps that runs without an \
assistant deciding anything -- the way the user asks. You get the workflow \
as JSON, the user's request, and the conversation around it for context. \
Reply with one JSON object and nothing else:

{"workflow": {"version": 1, "inputs": [...], "steps": [...]}, \
"changes": ["<one short line per change, in the user's language>"], \
"notes": ["<one line per thing the reviewer should check>"]}

Change only what the request needs: every other input and step, and every \
id, stays exactly as it is. If the request can't be done with the step \
kinds and tools below, reply {"error": "<why, in the user's language>"}.

The step format ("the conversation" below means the one you're given):

"""
    + STEP_FORMAT
)


class DraftFailed(Exception):
    """The conversation couldn't be turned into a workflow."""


@dataclass
class WorkflowDraft:
    name: str
    workflow: dict[str, Any]
    notes: list[str]
    # For a revision of a saved workflow: what was changed, one line each.
    changes: list[str] | None = None

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {"name": self.name, "workflow": self.workflow, "notes": self.notes}
        if self.changes is not None:
            data["changes"] = self.changes
        return data


def _clip(text: str, limit: int) -> str:
    return text if len(text) <= limit else f"{text[:limit]}… [{len(text) - limit} more characters]"


def _as_json(value: Any) -> str:
    return value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, default=str)


_BARE_REF = re.compile(r"(?:f\d+)?e\d+")
# A snapshot line: '- checkbox "All items" [ref=e322] [checked]'.
_SNAPSHOT_LINE = re.compile(r'^\s*- ([a-z]+)( ".*")? \[ref=((?:f\d+)?e\d+)\]')
# What an action reports it acted on: 'Clicked checkbox "All items".'
_ACTED_ON = re.compile(r"^(?:Clicked|Typed into|Hovering over|Uploaded .+ to) (.+)\.$", re.M)


def _element_names(snapshot: str) -> dict[str, str]:
    """Ref -> the element as the browser resolves a description: its
    snapshot line's role and name, with " #n" for the n-th alike."""
    seen: dict[str, int] = {}
    names = {}
    for line in snapshot.splitlines():
        match = _SNAPSHOT_LINE.match(line)
        if not match:
            continue
        base = f"{match[1]}{match[2] or ''}"
        seen[base] = seen.get(base, 0) + 1
        names[match[3]] = base if seen[base] == 1 else f"{base} #{seen[base]}"
    return names


def describe_browser_refs(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The tool calls with each browser ref replaced by the element it
    named, so a workflow drafted from them still finds it after a reload,
    when the page numbers its refs afresh."""
    names: dict[str, str] = {}
    out = []
    for entry in entries:
        if entry["kind"] != "tool" or not str(entry.get("tool_name", "")).startswith("browser_"):
            out.append(entry)
            continue
        result = _as_json(entry.get("result") or "")
        if entry["tool_name"] == "browser_snapshot":
            names.update(_element_names(result))
        args = entry.get("arguments")
        ref = args.get("ref") if isinstance(args, dict) else None
        if isinstance(args, dict) and isinstance(ref, str) and _BARE_REF.fullmatch(ref.strip()):
            acted = _ACTED_ON.search(result)
            name = names.get(ref.strip()) or (acted[1] if acted else None)
            if name:
                entry = {**entry, "arguments": {**args, "ref": name}}
        out.append(entry)
    return out


def render_conversation(history: list[dict[str, Any]]) -> tuple[str, list[str]]:
    """The conversation as the curator reads it, and the tools it used
    successfully, in first-use order. `history` is the replay entries
    (`serialize_history_for_ws_lg`): the caller serializes, because
    `runtime_lg` imports this package."""
    lines: list[str] = []
    used: list[str] = []
    call_number = 0
    for entry in describe_browser_refs(history):
        if entry["kind"] == "user":
            lines.append(f"[user] {_clip(entry['text'], _TEXT_CHARS)}")
        elif entry["kind"] == "agent":
            lines.append(f"[assistant] {_clip(entry['text'], _TEXT_CHARS)}")
        else:
            call_number += 1
            args = _clip(_as_json(entry["arguments"]), _ARGS_CHARS)
            result = _clip(_as_json(entry["result"]), _RESULT_CHARS)
            if entry["is_error"]:
                lines.append(f"[tool call #{call_number}, FAILED] {entry['tool_name']}({args})")
                lines.append(f"  error: {result}")
            else:
                lines.append(f"[tool call #{call_number}] {entry['tool_name']}({args})")
                lines.append(f"  result: {result}")
                if entry["tool_name"] not in used:
                    used.append(entry["tool_name"])
    transcript = "\n".join(lines)
    if len(transcript) > _TRANSCRIPT_CHARS:
        # The opening request says what the task is; the end is where it
        # got done. The middle is the likeliest to be exploration.
        half = _TRANSCRIPT_CHARS // 2
        transcript = (
            f"{transcript[:half]}\n[… middle of the conversation left out …]\n{transcript[-half:]}"
        )
    return transcript, used


def describe_tools(names: list[str], tools: dict[str, Any]) -> str:
    lines = []
    for name in names:
        if name in UNAVAILABLE_TOOLS or name not in tools:
            continue
        if name == SCRIPT_TOOL:
            lines.append(f'- {SCRIPT_TOOL}: becomes a "script" step, not a tool step')
            continue
        doc = tool_description(tools[name])
        params = ", ".join(
            f"{p['name']}{'' if p['required'] else '?'}: {p['type']}"
            + (f" -- {p['description']}" if p["description"] else "")
            for p in describe_params(tools[name])
        )
        lines.append(f"- {name}({params})\n  {_clip(doc, 300)}")
    return "\n".join(lines) or "(none)"


def check_draft(workflow: Workflow, tools: dict[str, Any]) -> list[str]:
    """What stops this workflow from running here, beyond what the spec
    itself enforces."""
    if not workflow.steps:
        return ["the workflow has no steps"]
    problems = []
    model_results = {p.step.save_as for p in walk(workflow.steps) if isinstance(p.step, LLMStep)}
    node_results = {
        p.step.save_as
        for p in walk(workflow.steps)
        if isinstance(p.step, ToolStep) and p.step.tool == "run_node_script"
    }
    for placed in walk(workflow.steps):
        step, index = placed.step, placed.number
        for reference in step_references(step):
            name, _, field = reference.partition(".")
            if name in node_results and field and field.split(".")[0] not in _NODE_RESULT:
                problems.append(
                    f"step {index}: {name} holds run_node_script's stdout, stderr and "
                    f"exit_code, not {field}; have the script throw when it is wrong"
                )
        if isinstance(step, LoopStep) and step.collect in model_results:
            # A model step's result is always an object of its fields; a
            # list of those is rarely what the steps after the loop expect.
            problems.append(
                f"step {index}: collect a field of {step.collect} (like {step.collect}.<field>), "
                "not the whole result"
            )
        if not isinstance(step, ToolStep):
            continue
        if step.tool == SCRIPT_TOOL:
            problems.append(f"step {index}: use a script step instead of calling {SCRIPT_TOOL}")
            continue
        if step.tool in UNAVAILABLE_TOOLS or step.tool not in tools:
            problems.append(f"step {index}: there's no tool called {step.tool!r} to use")
            continue
        ref = step.args.get("ref")
        if step.tool.startswith("browser_") and isinstance(ref, str) and _BARE_REF.fullmatch(ref):
            problems.append(
                f"step {index}: ref {ref!r} only existed on the conversation's page; name the "
                "element as the snapshot printed it, e.g. 'checkbox \"All items\"'"
            )
        params = {p["name"]: p for p in describe_params(tools[step.tool])}
        unknown = sorted(set(step.args) - set(params))
        if unknown:
            problems.append(f"step {index}: {step.tool} takes no {', '.join(unknown)}")
        missing = [n for n, p in params.items() if p["required"] and n not in step.args]
        if missing:
            problems.append(f"step {index}: {step.tool} needs {', '.join(missing)}")
    return problems


def with_read_tools(workflow: Workflow, tools: dict[str, Any]) -> Workflow:
    """Every bounded agent step may also list, inspect and read files: reading inside the
    workspace is what such a step does first, and is no new reach to consent to."""
    for placed in walk(workflow.steps):
        step = placed.step
        if isinstance(step, AgentStep) and step.autonomy == "bounded":
            step.tools += [t for t in READ_TOOLS if t in tools and t not in step.tools]
    return workflow


def _reply_object(text: str) -> dict[str, Any]:
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < start:
        raise ValueError("the reply has no JSON object")
    data = json.loads(text[start : end + 1])
    if not isinstance(data, dict):
        raise ValueError("the reply isn't a JSON object")
    return data


def _reply_text(message: Any) -> str:
    content = message.content
    if isinstance(content, str):
        return content
    return "".join(
        block.get("text", "") if isinstance(block, dict) else str(block) for block in content
    )


def _parse_reply(text: str, tools: dict[str, Any], name_hint: str) -> WorkflowDraft:
    """The draft, or ValueError with every problem the curator should fix."""
    data = _reply_object(text)
    if "error" in data and "workflow" not in data:
        raise DraftFailed(str(data["error"]))
    try:
        workflow = parse_workflow(data.get("workflow"))
    except ValidationError as exc:
        raise ValueError(workflow_error(exc, data.get("workflow"))) from exc
    problems = check_draft(workflow, tools)
    if problems:
        raise ValueError("; ".join(problems))
    workflow = with_read_tools(workflow, tools)
    notes = data.get("notes") or []
    if isinstance(notes, str):
        notes = [notes]
    name = name_hint or str(data.get("name") or "").strip() or "Untitled workflow"
    return WorkflowDraft(
        name=name[:120],
        workflow=workflow.model_dump(mode="json"),
        notes=[str(n) for n in notes if str(n).strip()],
    )


async def draft_workflow(
    model: Any,
    history: list[dict[str, Any]],
    tools: dict[str, Any],
    name_hint: str = "",
) -> WorkflowDraft:
    transcript, used = render_conversation(history)
    if not used:
        raise DraftFailed(
            "This conversation hasn't used any tools yet, so there's nothing to repeat. "
            "Do the task once here first."
        )
    if "temperature" in getattr(type(model), "model_fields", {}):
        model = model.model_copy(update={"temperature": 0})
    name_line = f'Name the workflow "{name_hint}".\n\n' if name_hint else ""
    conversation: list[Any] = [
        SystemMessage(CURATOR_INSTRUCTIONS),
        HumanMessage(
            f"{name_line}Tools you can use:\n{describe_tools(used, tools)}\n\n"
            f"The conversation:\n\n{transcript}"
        ),
    ]
    problem = ""
    for _attempt in range(MAX_ATTEMPTS):
        # Untagged, a call made inside the chat's own graph (the
        # draft_workflow tool) streams into the chat as if the assistant
        # were typing the draft.
        reply = await model.ainvoke(conversation, config={"tags": [TAG_NOSTREAM]})
        text = _reply_text(reply)
        try:
            return _parse_reply(text, tools, name_hint)
        except (ValueError, TypeError) as exc:
            problem = str(exc)
        conversation += [
            AIMessage(text),
            HumanMessage(f"That draft doesn't work: {problem}. Reply with the corrected JSON."),
        ]
    raise DraftFailed(
        f"Couldn't draft a valid workflow ({problem}). Try again, or build it by hand."
    )


def _lines(value: Any) -> list[str]:
    items = [value] if isinstance(value, str) else (value or [])
    return [str(item) for item in items if str(item).strip()]


def _parse_revision(text: str, tools: dict[str, Any], name: str) -> WorkflowDraft:
    data = _reply_object(text)
    if "error" in data and "workflow" not in data:
        raise DraftFailed(str(data["error"]))
    try:
        workflow = parse_workflow(data.get("workflow"))
    except ValidationError as exc:
        raise ValueError(workflow_error(exc, data.get("workflow"))) from exc
    problems = check_draft(workflow, tools)
    if problems:
        raise ValueError("; ".join(problems))
    workflow = with_read_tools(workflow, tools)
    changes = _lines(data.get("changes"))
    if not changes:
        raise ValueError('list what you changed in "changes"')
    return WorkflowDraft(
        name=name,
        workflow=workflow.model_dump(mode="json"),
        notes=_lines(data.get("notes")),
        changes=changes,
    )


def _tools_in(workflow: dict[str, Any]) -> list[str]:
    try:
        parsed = parse_workflow(workflow)
    except ValidationError:
        return []
    return [p.step.tool for p in walk(parsed.steps) if isinstance(p.step, ToolStep)]


def _keep_marks(saved: dict[str, Any], draft: WorkflowDraft) -> WorkflowDraft:
    """A revision keeps every step the workflow it revises marks as one that can't be taken
    back (decision 0029): a test run stops before it, and a model asked to make a test pass
    unmarks it. Only the person can, in the editor."""
    try:
        marked = {
            p.step.id
            for p in walk(parse_workflow(saved).steps)
            if getattr(p.step, "irreversible", False)
        }
    except ValidationError:
        return draft
    kept = []
    for placed in walk(parse_workflow(draft.workflow).steps):
        if placed.step.id in marked and not getattr(placed.step, "irreversible", False):
            kept.append(placed.step)
    if not kept:
        return draft
    ids = {step.id for step in kept}

    def mark(steps: list[Any]) -> None:
        for step in steps:
            if step.get("id") in ids:
                step["irreversible"] = True
            for children in raw_child_lists(step):
                mark(children)

    mark(draft.workflow.get("steps") or [])
    titles = ", ".join(f'"{step.title}"' for step in kept)
    note = f"Kept {titles} marked as a step that can't be taken back; only you can unmark it."
    return WorkflowDraft(draft.name, draft.workflow, draft.notes, [*(draft.changes or []), note])


async def revise_workflow(
    model: Any,
    name: str,
    workflow: dict[str, Any],
    request: str,
    history: list[dict[str, Any]],
    tools: dict[str, Any],
) -> WorkflowDraft:
    """The saved `workflow` changed as `request` asks, checked like a new
    draft, with a line per change for the person reviewing it."""
    transcript, used = render_conversation(history)
    if "temperature" in getattr(type(model), "model_fields", {}):
        model = model.model_copy(update={"temperature": 0})
    described = list(dict.fromkeys([*_tools_in(workflow), *used, SCRIPT_TOOL]))
    others = sorted(t for t in tools if t not in described and t not in UNAVAILABLE_TOOLS)
    conversation: list[Any] = [
        SystemMessage(REVISER_INSTRUCTIONS),
        HumanMessage(
            f"The workflow, {name!r}:\n{json.dumps(workflow, ensure_ascii=False)}\n\n"
            f"The user's request: {request}\n\n"
            f"Tools:\n{describe_tools(described, tools)}\n"
            f"Other tools (you'll get their parameters if you use one): {', '.join(others)}\n\n"
            f"The conversation:\n\n{transcript or '(nothing yet)'}"
        ),
    ]
    problem = ""
    for _attempt in range(MAX_ATTEMPTS):
        reply = await model.ainvoke(conversation, config={"tags": [TAG_NOSTREAM]})
        text = _reply_text(reply)
        try:
            return _keep_marks(workflow, _parse_revision(text, tools, name))
        except (ValueError, TypeError) as exc:
            problem = str(exc)
        try:
            proposed = _tools_in(_reply_object(text).get("workflow") or {})
        except (ValueError, TypeError):
            proposed = []
        newly_used = [t for t in dict.fromkeys(proposed) if t not in described]
        described += newly_used
        extra = f"\n\nThose tools take:\n{describe_tools(newly_used, tools)}" if newly_used else ""
        conversation += [
            AIMessage(text),
            HumanMessage(f"That doesn't work: {problem}. Reply with the corrected JSON.{extra}"),
        ]
    raise DraftFailed(f"Couldn't revise the workflow ({problem}). Try again, or edit it by hand.")
