"""The checks saving a workflow makes, walking its steps in the order they'd run: every name a
step reads is an input or an earlier step's result at that point, and the limits on steps and
nesting hold."""

from __future__ import annotations

from .reads import _condition_refs, step_references, step_templates
from .refs import malformed_templates
from .spec import (
    FAILURE,
    MAX_NESTING,
    MAX_STEPS,
    MEMORY,
    RUN_FIELDS,
    THIS_RUN,
    AgentStep,
    AskStep,
    BranchStep,
    CheckStep,
    ChoiceStep,
    LLMStep,
    LoopStep,
    MemoryEntry,
    OnFailure,
    RememberStep,
    Step,
    WaitStep,
    WorkflowInput,
    _Recovers,
    _root,
    child_lists,
    failure_policy,
    step_output,
)


class _Scope:
    """Save-time checks, walking the steps in the order they'd run."""

    def __init__(self, inputs: list[WorkflowInput]) -> None:
        self.number = 0
        self.ids: set[str] = set()
        self.taken = {i.name for i in inputs}
        # Names that exist only inside a loop or one arm, for a clearer
        # message when a later step reads one.
        self.scoped: set[str] = set()
        # A model or agent step's result is exactly its declared fields.
        self.fields: dict[str, set[str]] = {}
        self.agents = 0
        # How many steps-in-place-of-a-failed-one surround the steps being checked, where
        # `failure` is theirs to read.
        self.fallbacks = 0

    def remembers(self, memory: list[MemoryEntry]) -> set[str]:
        """The names the steps may read from the start: the inputs, and with memory, `memory`
        and `run` (decision 0034)."""
        available = set(self.taken)
        if not memory:
            return available
        if len({m.name for m in memory}) != len(memory):
            raise ValueError("each value a task remembers has its own name")
        for reserved in (MEMORY, THIS_RUN):
            if reserved in self.taken:
                raise ValueError(f"a task that remembers reads {reserved!r}; rename that input")
        self.taken |= {MEMORY, THIS_RUN}
        self.fields |= {MEMORY: {m.name for m in memory}, THIS_RUN: set(RUN_FIELDS)}
        return available | {MEMORY, THIS_RUN}

    def _field(self, reference: str, where: str) -> None:
        root, _, rest = reference.partition(".")
        fields = self.fields.get(root)
        field_name = rest.split(".", 1)[0]
        if fields is not None and rest and field_name not in fields:
            raise ValueError(
                f"{where} reads {reference!r}, but {root} only has " + ", ".join(sorted(fields))
            )

    def check(self, steps: list[Step], available: set[str], depth: int) -> set[str]:
        """Returns the names available after `steps`."""
        available = set(available)
        for step in steps:
            self.number += 1
            where = f"step {self.number} ({step.title!r})"
            if self.number > MAX_STEPS:
                raise ValueError(f"a workflow has at most {MAX_STEPS} steps, nested ones included")
            if step.id in self.ids:
                raise ValueError(f"step {self.number}: id {step.id!r} is used twice")
            self.ids.add(step.id)
            for text in step_templates(step):
                for bad in malformed_templates(text):
                    raise ValueError(
                        f"{where}: {bad} isn't a reference -- write "
                        "{{name}} or {{name.field}}, with no other expressions"
                    )
            for reference in step_references(step):
                if _root(reference) not in available:
                    raise ValueError(
                        f"{where} reads {reference!r}, which isn't an input or the result of "
                        "an earlier step" + _scope_hint(reference, self.scoped)
                    )
                self._field(reference, where)
            self.agents += isinstance(step, AgentStep)
            self._ends_or_remembers(step, where, depth)
            if isinstance(step, (BranchStep, ChoiceStep, LoopStep)) and depth >= MAX_NESTING:
                raise ValueError(f"{where}: branches and loops nest at most {MAX_NESTING} deep")
            if isinstance(step, (BranchStep, ChoiceStep)):
                available |= self._paths(step, available, depth)
                continue
            if isinstance(step, LoopStep):
                self._loop(step, where, available, depth)
            policy = failure_policy(step)
            if policy is not None:
                available |= self._recovery(step, policy, where, available, depth)
                continue
            self._save(step)
            output = step_output(step)
            available |= {output} if output else set()
        return available

    def _ends_or_remembers(self, step: Step, where: str, depth: int) -> None:
        if isinstance(step, CheckStep) and step.otherwise == "end" and (depth or self.fallbacks):
            raise ValueError(f"{where}: only a check outside loops and branches ends the run")
        if isinstance(step, RememberStep) and step.name not in self.fields.get(MEMORY, set()):
            raise ValueError(f"{where} remembers {step.name!r}, which the task doesn't keep")

    def _save(self, step: Step) -> None:
        output = step_output(step)
        if output is None:
            return
        if output in self.taken:
            raise ValueError(f"step {self.number}: {output!r} is already taken")
        self.taken.add(output)
        if isinstance(step, (LLMStep, AgentStep)):
            self.fields[output] = _result_fields(step)
        elif isinstance(step, AskStep):
            self.fields[output] = {f.name for f in step.fields}
        elif isinstance(step, WaitStep):
            self.fields[output] = {"path", "found"}

    def _recovery(
        self, step: Step, policy: OnFailure, where: str, available: set[str], depth: int
    ) -> set[str]:
        """What a step with something to do when it fails leaves for later steps: its result,
        unless a failure skips it or the steps in its place don't make the same name."""
        output = step_output(step)
        mine = {output} if output else set()
        before = set(self.taken)
        self._save(step)
        if policy.then != "steps":
            if policy.then == "skip":
                self.scoped |= mine
                return set()
            return mine
        if FAILURE in before and not self.fallbacks:
            raise ValueError(
                f"{where}: the steps in its place read {FAILURE!r}, so no input or earlier step "
                "may be called that"
            )
        taken = set(self.taken)
        self.taken = before | {FAILURE}
        self.fallbacks += 1
        made = self.check(policy.steps, available | {FAILURE}, depth + 1) - available
        self.fallbacks -= 1
        self.taken = (taken | self.taken) - ({FAILURE} - before)
        kept = mine & made
        self.scoped |= (mine | made) - kept - {FAILURE}
        return kept

    def after_failure(self, steps: list[Step], inputs: set[str]) -> None:
        for step in steps:
            if not isinstance(step, _Recovers) or (
                step.on_failure and step.on_failure.then == "steps"
            ):
                raise ValueError(
                    f"after a failed run come actions, programs, model and agent steps, "
                    f"with nothing in their place, not {step.title!r}"
                )
        if FAILURE in self.taken:
            raise ValueError(
                f"the steps after a failed run read {FAILURE!r}, so no input or step may be "
                "called that"
            )
        self.taken.add(FAILURE)
        self.fallbacks += 1
        self.check(steps, inputs | {FAILURE}, 1)

    def _paths(self, step: BranchStep | ChoiceStep, available: set[str], depth: int) -> set[str]:
        # Each path may produce the same names -- that's how a value set
        # whichever way it went is read after the branch.
        before = set(self.taken)
        taken = set(before)
        made: list[set[str]] = []
        for _arm, steps in child_lists(step):
            self.taken = set(before)
            made.append(self.check(steps, available, depth + 1) - available)
            taken |= self.taken
        self.taken = taken
        merged = set.intersection(*made)
        self.scoped |= set.union(*made) - merged
        return merged

    def _loop(self, step: LoopStep, where: str, available: set[str], depth: int) -> None:
        if step.item in self.taken:
            raise ValueError(f"{where}: {step.item!r} is already taken, name the item differently")
        # A body's names exist per item, so they're free again after the
        # loop -- two loops in a row can both call their item `item`.
        before = set(self.taken)
        self.taken.add(step.item)
        after_body = self.check(step.steps, available | {step.item}, depth + 1)
        if step.collect is not None and _root(step.collect) in after_body - available:
            self._field(step.collect, where)
        if step.collect is not None and _root(step.collect) not in after_body - available:
            raise ValueError(
                f"{where} collects {step.collect!r}, which isn't the item or a result of "
                "a step inside the loop"
            )
        for reference in (r for c in step.until for r in _condition_refs(c)):
            if _root(reference) not in after_body:
                raise ValueError(
                    f"{where} stops early by {reference!r}, which isn't an input, the item or "
                    "a result of a step before the loop or inside it"
                )
            self._field(reference, where)
        self.scoped |= self.taken - before
        self.taken = before


def _result_fields(step: LLMStep | AgentStep) -> set[str]:
    if isinstance(step, AgentStep):
        return step.result_fields()
    return {f.name for f in step.fields}


def _scope_hint(reference: str, scoped: set[str]) -> str:
    if _root(reference) in scoped:
        return (
            " here (it's made inside a loop, in only one arm of a branch, or by a step that is "
            "skipped when it fails)"
        )
    return ""
