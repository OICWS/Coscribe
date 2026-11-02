"""A workflow's definition: named inputs and an ordered list of steps, each
one of a few kinds with deliberately little autonomy. Stored as JSON on the
scheduled task that runs it.

Every value a step reads from an earlier one goes through a reference that
validate() checks against what's actually been produced by that point, so
a typo or a reordered step fails when the workflow is saved, not halfway
through a run.

Branches, choices and loops hold their own step lists, and scope what
they produce: after a branch or a choice, only a name every path produces
is certain to exist; a loop body's names are per item, so only the loop's collected
list is visible after it. Steps are numbered in document order, nested
ones included -- the numbers the editor and the run view show."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import PurePosixPath, PureWindowsPath
from typing import Annotated, Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_serializer,
    model_validator,
)

from .inputs import InputType, input_problem
from .refs import (
    conditions_hold,
    is_reference,
    resolve,
    same_choice,
    template_references,
)

IDENTIFIER = re.compile(r"^[a-z][a-z0-9_]{0,39}$")

FieldType = Literal["text", "number", "boolean", "list"]
CheckOp = Literal[
    "eq", "ne", "gt", "ge", "lt", "le",
    "contains", "not_contains", "starts_with", "ends_with",
    "not_empty", "empty", "before", "after",
]  # fmt: skip
UNARY_OPS = frozenset({"not_empty", "empty"})
# Whether every condition of a list must hold, or one is enough (decision 0031).
Match = Literal["all", "any"]


def _identifier(value: str) -> str:
    if not IDENTIFIER.fullmatch(value):
        raise ValueError(
            f"{value!r} must start with a lowercase letter and use only a-z, 0-9 and _ "
            "(at most 40 characters)"
        )
    return value


class _Model(BaseModel):
    # By name and by alias: a choice case's `is` is a Python keyword.
    model_config = ConfigDict(extra="forbid", validate_by_name=True, serialize_by_alias=True)


class WorkflowInput(_Model):
    name: str
    label: str = ""
    type: InputType = "text"
    # A date's may be relative ("last_month_start"), worked out when each run starts.
    default: str | float | bool | None = None
    # A choice's options, in order.
    options: list[str] = []
    # An optional input may be left blank at run time; its steps get "".
    required: bool = True

    _check_name = field_validator("name")(_identifier)
    _check_default = model_validator(mode="after")(lambda spec: _input_fits(spec))


def _input_fits(spec: WorkflowInput) -> WorkflowInput:
    problem = input_problem(spec.type, spec.default, spec.options)
    if problem:
        raise ValueError(f"input {spec.name!r}: {problem}")
    return spec


class OutputField(_Model):
    name: str
    type: FieldType = "text"
    description: str = ""

    _check_name = field_validator("name")(_identifier)


class Operand(_Model):
    """Exactly one of: `ref` (a value by reference, e.g. "summary.error_count"),
    `count` (the length of a referenced list/text), or `value` (a literal)."""

    ref: str | None = None
    count: str | None = None
    value: Any = None

    @model_validator(mode="after")
    def _exactly_one(self) -> Operand:
        if len(self.model_fields_set) != 1:
            raise ValueError("an operand is exactly one of ref, count or value")
        return self

    @model_serializer
    def _only_the_one_set(self) -> dict[str, Any]:
        # The unset two would come back as explicit nulls and fail
        # _exactly_one when a saved workflow is loaded again.
        key = next(iter(self.model_fields_set))
        return {key: getattr(self, key)}

    def reference(self) -> str | None:
        return self.ref if self.ref is not None else self.count


class Condition(_Model):
    left: Operand
    op: CheckOp
    right: Operand | None = None

    @model_validator(mode="after")
    def _right_unless_unary(self) -> Condition:
        if (self.op in UNARY_OPS) != (self.right is None):
            raise ValueError(
                "empty and not_empty take no right-hand side; every other op needs one"
            )
        return self


def _one_condition_as_a_list(data: Any, old: str, new: str) -> Any:
    # Saved before decision 0031, a branch had one `condition` and an approval one `when`.
    if isinstance(data, dict) and old in data and (old != new or not isinstance(data[old], list)):
        data = dict(data)
        single = data.pop(old)
        data[new] = [] if single is None else [single]
    return data


class _Step(_Model):
    id: str
    title: str = Field(min_length=1, max_length=120)

    _check_id = field_validator("id")(_identifier)


MAX_RETRIES = 5
MAX_RETRY_WAIT = 300
# What the steps that run because a step failed read about it: {"step", "message"}.
FAILURE = "failure"


class OnFailure(_Model):
    """What a step does when it still fails (decision 0032): try again `retries` times,
    `wait_seconds` apart, then stop the run, skip the step, or run `steps` in its place."""

    retries: int = Field(default=0, ge=0, le=MAX_RETRIES)
    wait_seconds: int = Field(default=30, ge=0, le=MAX_RETRY_WAIT)
    then: Literal["stop", "skip", "steps"] = "stop"
    # Empty while it's being built; preflight refuses to run it so.
    steps: list[Step] = []

    _steps_only_for_steps = model_validator(mode="after")(
        lambda failure: _only_steps_run_steps(failure)
    )


def _only_steps_run_steps(failure: OnFailure) -> OnFailure:
    if failure.then != "steps" and failure.steps:
        raise ValueError(
            f"steps run in a failed step's place only with then: steps, not {failure.then}"
        )
    return failure


def _never_retried(step: _Recovers) -> _Recovers:
    # Trying again could send, pay or delete twice.
    if step.on_failure and step.on_failure.retries and getattr(step, "irreversible", False):
        raise ValueError(
            "a step that can't be undone is never tried again on its own; give it no retries"
        )
    return step


class _Recovers(_Step):
    """A step that does work which can fail for reasons outside the workflow."""

    on_failure: OnFailure | None = None

    _check_retries = model_validator(mode="after")(lambda step: _never_retried(step))


def failure_policy(step: Step) -> OnFailure | None:
    """What `step` does when it fails; None when a failure stops the run at once."""
    return step.on_failure if isinstance(step, _Recovers) else None


class ToolStep(_Recovers):
    kind: Literal["tool"] = "tool"
    tool: str
    args: dict[str, Any] = {}
    save_as: str | None = None
    # It sends, submits, pays or deletes something outside this machine that
    # can't be taken back: a test run stops before it (decision 0029).
    irreversible: bool = False

    _check_save_as = field_validator("save_as")(lambda v: v if v is None else _identifier(v))


class ScriptStep(_Recovers):
    """A fixed Python script, reviewed once when the workflow is saved. It
    reads earlier values from a ready-made `inputs` dict (never spliced into
    the code), and its result is the JSON it prints on its last line."""

    kind: Literal["script"] = "script"
    code: str = Field(min_length=1)
    inputs: dict[str, Any] = {}
    save_as: str | None = None

    _check_save_as = field_validator("save_as")(lambda v: v if v is None else _identifier(v))


class LLMStep(_Recovers):
    """One model call, no tools, that must return exactly `fields`."""

    kind: Literal["llm"] = "llm"
    prompt: str = Field(min_length=1)
    fields: list[OutputField] = Field(min_length=1)
    model: str | None = None
    save_as: str

    _check_save_as = field_validator("save_as")(_identifier)


class CheckStep(_Step):
    """The conditions must hold (all of them, or any one by `match`), or the run stops here."""

    kind: Literal["check"] = "check"
    conditions: list[Condition] = Field(min_length=1)
    match: Match = "all"


class ApprovalStep(_Step):
    """Pause until a person approves -- only when `when` holds, if it lists any."""

    kind: Literal["approval"] = "approval"
    message: str = Field(min_length=1)
    when: list[Condition] = []
    match: Match = "all"

    _legacy = model_validator(mode="before")(
        lambda data: _one_condition_as_a_list(data, "when", "when")
    )


MAX_NESTING = 3
MAX_STEPS = 100
MAX_LOOP_ITEMS = 200
MAX_CHOICE_CASES = 12
MAX_AGENT_STEPS = 60

Autonomy = Literal["bounded", "high", "full"]
# What an agent step's result holds when it names no fields.
AGENT_REPORT_FIELD = "report"
# Whether the agent finished, which every agent step's report gives
# (`workflows.agent_step`); a field of the step can't take these names.
AGENT_OUTCOME_FIELDS = frozenset({"outcome", "stopped_because", "assumed"})


def _is_absolute_path(text: str) -> bool:
    return PurePosixPath(text).is_absolute() or PureWindowsPath(text).is_absolute()


def _agent_is_consistent(step: AgentStep) -> AgentStep:
    if step.autonomy == "bounded" and not step.tools:
        raise ValueError("a bounded agent step lists the tools it may call")
    if step.autonomy != "bounded" and step.tools:
        raise ValueError(
            f"a {step.autonomy} agent step has the environment's tools; "
            "list tools only for a bounded one"
        )
    if len(set(step.tools)) != len(step.tools):
        raise ValueError("each tool is listed once")
    if step.autonomy == "full" and step.fields:
        raise ValueError("a full agent step reports in prose; give it no fields")
    if len({f.name for f in step.fields}) != len(step.fields):
        raise ValueError("field names must be unique")
    reserved = {f.name for f in step.fields} & AGENT_OUTCOME_FIELDS
    if reserved:
        raise ValueError(f"{', '.join(sorted(reserved))} is the agent's own verdict; rename it")
    # A relative folder would resolve against wherever the server runs.
    relative = [f for f in step.folders if not _is_absolute_path(f)]
    if relative:
        raise ValueError(f"folders must be full paths, not {', '.join(map(repr, relative))}")
    return step


class AgentStep(_Recovers):
    """An agent working toward `goal` with tools, within limits (decision
    0028). "bounded" may call only `tools` and touch only the declared
    `folders` and `sites` -- what saving consents to; "high" has the
    environment's tools under the task's approval mode; "full" is the whole
    task as one agent and reports in prose. The result is `fields` when
    given, else {"report": <the agent's reply>}."""

    kind: Literal["agent"] = "agent"
    autonomy: Autonomy = "bounded"
    goal: str = Field(min_length=1)
    tools: list[str] = []
    folders: list[str] = []
    sites: list[str] = []
    fields: list[OutputField] = []
    # Model calls, the same unit as a sub-agent's step cap.
    max_steps: int = Field(default=20, ge=1, le=MAX_AGENT_STEPS)
    model: str | None = None
    save_as: str | None = None
    # The person's word, given when saving, that what this step reads from
    # outside may be acted on with its tools: it is then not read-only.
    trusted_input: bool = False
    # As a tool step's: a test run stops before the whole step (decision 0029).
    irreversible: bool = False

    _check_save_as = field_validator("save_as")(lambda v: v if v is None else _identifier(v))

    _check_tools = model_validator(mode="after")(lambda step: _agent_is_consistent(step))

    def result_fields(self) -> set[str]:
        return {f.name for f in self.fields} or {AGENT_REPORT_FIELD}


class BranchStep(_Step):
    """Runs `then` when the conditions hold (all, or any one by `match`), else `otherwise`."""

    kind: Literal["branch"] = "branch"
    conditions: list[Condition] = Field(min_length=1)
    match: Match = "all"
    then: list[Step] = []
    otherwise: list[Step] = []

    _legacy = model_validator(mode="before")(
        lambda data: _one_condition_as_a_list(data, "condition", "conditions")
    )


class ChoiceCase(_Model):
    is_: str = Field(alias="is", min_length=1, max_length=200)
    steps: list[Step] = []


class ChoiceStep(_Step):
    """Runs the steps of the first case whose `is` the value of `value` equals (as text, ignoring
    case and surrounding spaces), else `otherwise` (decision 0031)."""

    kind: Literal["choice"] = "choice"
    value: str
    cases: list[ChoiceCase] = Field(min_length=1, max_length=MAX_CHOICE_CASES)
    otherwise: list[Step] = []

    _check_value = field_validator("value")(lambda value: _choice_value(value))
    _check_cases = model_validator(mode="after")(lambda step: _cases_differ(step))


def _choice_value(value: str) -> str:
    if not is_reference(value):
        raise ValueError(f"{value!r} isn't a name like department or report.status")
    return value


def _cases_differ(step: ChoiceStep) -> ChoiceStep:
    seen = [case.is_.strip().casefold() for case in step.cases]
    if len(set(seen)) != len(seen):
        raise ValueError("each path of a choice needs a different value")
    return step


class LoopStep(_Step):
    """Runs `steps` once per item of the list `over`, in order, with the
    item as `item`. `save_as` gets the list of each pass's `collect`."""

    kind: Literal["loop"] = "loop"
    over: str
    item: str = "item"
    steps: list[Step] = []
    collect: str | None = None
    save_as: str | None = None
    # A longer list fails the loop rather than being cut short.
    max_items: int = Field(default=50, ge=1, le=MAX_LOOP_ITEMS)
    # Checked after each pass, with the item and that pass's results: when they hold, the loop
    # ends early and keeps what it collected so far.
    until: list[Condition] = []
    match: Match = "all"
    # A pass that fails: stop the run, or record the item as skipped and go on to the next.
    on_item_failure: Literal["stop", "skip"] = "stop"

    _check_item = field_validator("item")(_identifier)
    _check_save_as = field_validator("save_as")(lambda v: v if v is None else _identifier(v))

    @field_validator("over", "collect")
    @classmethod
    def _a_reference(cls, value: str | None) -> str | None:
        if value is not None and not is_reference(value):
            raise ValueError(f"{value!r} isn't a name like matches or report.rows")
        return value

    @model_validator(mode="after")
    def _collects_what_it_saves(self) -> LoopStep:
        if (self.collect is None) != (self.save_as is None):
            raise ValueError(
                "collect and save_as go together: what to keep from each pass, "
                "and the name for the list"
            )
        return self


Step = Annotated[
    ToolStep | ScriptStep | LLMStep | AgentStep | CheckStep | ApprovalStep | BranchStep
    | ChoiceStep | LoopStep,
    Field(discriminator="kind"),
]  # fmt: skip
BlockStep = BranchStep | ChoiceStep | LoopStep


def _root(reference: str) -> str:
    return reference.split(".", 1)[0]


def _condition_refs(condition: Condition) -> list[str]:
    operands = [condition.left] + ([condition.right] if condition.right else [])
    return [r for o in operands if (r := o.reference()) is not None]


def step_references(step: Step) -> list[str]:
    """Every reference a step reads, as written."""
    if isinstance(step, ToolStep):
        return _value_references(step.args)
    if isinstance(step, ScriptStep):
        return _value_references(step.inputs)
    if isinstance(step, LLMStep):
        return template_references(step.prompt)
    if isinstance(step, AgentStep):
        return template_references(step.goal)
    if isinstance(step, CheckStep):
        return [r for c in step.conditions for r in _condition_refs(c)]
    if isinstance(step, ApprovalStep):
        return template_references(step.message) + [
            r for c in step.when for r in _condition_refs(c)
        ]
    if isinstance(step, BranchStep):
        return [r for c in step.conditions for r in _condition_refs(c)]
    if isinstance(step, ChoiceStep):
        return [step.value]
    if isinstance(step, LoopStep):
        # `until` reads the item and the body's results, checked where the body is.
        return [step.over]
    return []  # pragma: no cover -- every kind is handled above


def _value_references(value: Any) -> list[str]:
    if isinstance(value, str):
        return template_references(value)
    if isinstance(value, list):
        return [r for item in value for r in _value_references(item)]
    if isinstance(value, dict):
        return [r for item in value.values() for r in _value_references(item)]
    return []


def _texts(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [t for item in value for t in _texts(item)]
    if isinstance(value, dict):
        return [t for item in value.values() for t in _texts(item)]
    return []


def step_templates(step: Step) -> list[str]:
    """Every text of a step that references are filled into."""
    if isinstance(step, ToolStep):
        return _texts(step.args)
    if isinstance(step, ScriptStep):
        return _texts(step.inputs)
    if isinstance(step, LLMStep):
        return [step.prompt]
    if isinstance(step, AgentStep):
        return [step.goal]
    if isinstance(step, ApprovalStep):
        return [step.message]
    return []


def step_output(step: Step) -> str | None:
    return getattr(step, "save_as", None)


def child_lists(step: Step) -> list[tuple[str, list[Step]]]:
    """A block's own step lists, in document order."""
    if isinstance(step, BranchStep):
        return [("then", step.then), ("otherwise", step.otherwise)]
    if isinstance(step, ChoiceStep):
        cases = [(f"case:{index}", case.steps) for index, case in enumerate(step.cases)]
        return [*cases, ("otherwise", step.otherwise)]
    if isinstance(step, LoopStep):
        return [("steps", step.steps)]
    if isinstance(step, _Recovers) and step.on_failure:
        return [("fallback", step.on_failure.steps)]
    return []


def choose_arm(
    step: BranchStep | ChoiceStep, values: dict[str, Any]
) -> tuple[str, list[tuple[bool, Any, Any]]]:
    """Which of its paths a branch or a choice takes (a name `child_lists` gives), and what it
    compared to decide."""
    if isinstance(step, BranchStep):
        held, checked = conditions_hold(step.conditions, step.match, values)
        return ("then" if held else "otherwise"), checked
    value = resolve(step.value, values)
    for index, case in enumerate(step.cases):
        if same_choice(value, case.is_):
            return f"case:{index}", [(True, value, case.is_)]
    return "otherwise", [(False, value, [case.is_ for case in step.cases])]


@dataclass(frozen=True)
class Placed:
    """A step with where it sits: its document-order number and the ids of
    the loops around it, outermost first."""

    number: int
    step: Step
    loops: tuple[str, ...]


def walk(steps: list[Step]) -> list[Placed]:
    placed: list[Placed] = []

    def visit(items: list[Step], loops: tuple[str, ...]) -> None:
        for step in items:
            placed.append(Placed(len(placed) + 1, step, loops))
            inner = (*loops, step.id) if isinstance(step, LoopStep) else loops
            for _arm, children in child_lists(step):
                visit(children, inner)

    visit(steps, ())
    return placed


# A task's one autonomy switch (decision 0030), lowest first: a ceiling on
# what its steps may be.
TaskAutonomy = Literal["fixed", "self_healing", "proactive", "autonomous"]
TASK_AUTONOMY_LEVELS: tuple[TaskAutonomy, ...] = (
    "fixed",
    "self_healing",
    "proactive",
    "autonomous",
)


def step_autonomy(step: Step) -> TaskAutonomy:
    """The lowest task setting that allows this step."""
    if isinstance(step, AgentStep):
        return "autonomous" if step.autonomy == "full" else "proactive"
    return "fixed"


def needed_autonomy(steps: list[Step]) -> TaskAutonomy:
    """The lowest task setting that allows every step: what a workflow
    without the setting acts at."""
    levels = [TASK_AUTONOMY_LEVELS.index(step_autonomy(p.step)) for p in walk(steps)]
    return TASK_AUTONOMY_LEVELS[max(levels, default=0)]


def steps_above(steps: list[Step], ceiling: TaskAutonomy) -> list[Step]:
    limit = TASK_AUTONOMY_LEVELS.index(ceiling)
    return [
        p.step for p in walk(steps) if TASK_AUTONOMY_LEVELS.index(step_autonomy(p.step)) > limit
    ]


class Workflow(_Model):
    # Version 2 (decision 0028) may hold agent steps; a version 1 workflow
    # keeps behaving as it did when it was saved.
    version: Literal[1, 2] = 1
    inputs: list[WorkflowInput] = []
    # Empty is a workflow still being built on its task page; preflight
    # refuses to run one.
    steps: list[Step] = Field(default_factory=list, max_length=MAX_STEPS)
    # None: the lowest level its steps need (`needed_autonomy`).
    autonomy: TaskAutonomy | None = None
    # Run when a step fails and the run stops, not when a person said no (decision 0032).
    after_failure: list[Step] = Field(default_factory=list, max_length=MAX_STEPS)

    def effective_autonomy(self) -> TaskAutonomy:
        return self.autonomy or needed_autonomy(self.every_step())

    def every_step(self) -> list[Step]:
        """The steps of a run and those after a failed one, in the order they are numbered."""
        return [*self.steps, *self.after_failure]

    @model_validator(mode="after")
    def _names_resolve_in_order(self) -> Workflow:
        if len({i.name for i in self.inputs}) != len(self.inputs):
            raise ValueError("input names must be unique")
        # Here, not at the top: the checks read the step classes this module defines.
        from .scope import _Scope

        scope = _Scope(self.inputs)
        scope.check(self.steps, {i.name for i in self.inputs}, 0)
        scope.after_failure(self.after_failure, {i.name for i in self.inputs})
        if scope.agents and self.version < 2:
            raise ValueError("agent steps need a version 2 workflow")
        above = steps_above(self.every_step(), self.autonomy) if self.autonomy else []
        if above:
            names = ", ".join(f'"{step.title}"' for step in above)
            raise ValueError(
                f"the task's autonomy is {self.autonomy}, which doesn't allow {names}; "
                f"raise it to {needed_autonomy(self.every_step())} or change those steps"
            )
        return self


def parse_workflow(data: Any) -> Workflow:
    return Workflow.model_validate(data)


def current_shape(workflow: dict[str, Any] | None) -> dict[str, Any] | None:
    """A stored workflow as it is written now (one saved before decision 0031 had a branch's
    single `condition`), so whoever reads it reads one shape; one that no longer validates is
    kept as it was, for its run to say why."""
    if workflow is None:
        return None
    try:
        return parse_workflow(workflow).model_dump(mode="json")
    except ValidationError:
        return workflow


OnFailure.model_rebuild()
ToolStep.model_rebuild()
ScriptStep.model_rebuild()
LLMStep.model_rebuild()
AgentStep.model_rebuild()
BranchStep.model_rebuild()
ChoiceCase.model_rebuild()
ChoiceStep.model_rebuild()
LoopStep.model_rebuild()
Workflow.model_rebuild()
