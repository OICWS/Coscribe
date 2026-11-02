import type { BlockStep, RecoveringStep, Workflow, WorkflowStep } from "../types/workflow";

// Branches and loops hold their own step lists. A list is named by the
// block that holds it and which of its lists it is; ids are unique across
// the whole workflow, so that's enough to find it.

/** A choice's paths are "case:0", "case:1"..., then "otherwise". "fallback" is what runs in a
 * failed step's place; "after_failure" is the workflow's own list for a failed run. */
export type Arm = "then" | "otherwise" | "steps" | "fallback" | "after_failure" | `case:${number}`;

export interface ListRef {
  parent: string | null;
  arm: Arm | null;
}

export const ROOT: ListRef = { parent: null, arm: null };
export const AFTER_FAILURE: ListRef = { parent: null, arm: "after_failure" };

export function listKey(ref: ListRef): string {
  if (ref.parent === null) return ref.arm === "after_failure" ? "after_failure" : "root";
  return `${ref.parent}:${ref.arm}`;
}

export function isBlock(step: WorkflowStep): step is BlockStep {
  return step.kind === "branch" || step.kind === "choice" || step.kind === "loop";
}

export function canRecover(step: WorkflowStep): step is RecoveringStep {
  return (
    step.kind === "tool" ||
    step.kind === "script" ||
    step.kind === "llm" ||
    step.kind === "agent" ||
    step.kind === "run_task"
  );
}

/** The steps a run goes through and those after a failed one, in the order they are numbered
 * (workflow_spec's Workflow.every_step). */
export function everyStep(workflow: Workflow): WorkflowStep[] {
  return [...workflow.steps, ...(workflow.after_failure ?? [])];
}

export function childLists(step: WorkflowStep): [Arm, WorkflowStep[]][] {
  if (step.kind === "branch") {
    return [
      ["then", step.then],
      ["otherwise", step.otherwise],
    ];
  }
  if (step.kind === "choice") {
    return [
      ...step.cases.map((c, index): [Arm, WorkflowStep[]] => [`case:${index}`, c.steps]),
      ["otherwise", step.otherwise],
    ];
  }
  if (step.kind === "loop") return [["steps", step.steps]];
  if (canRecover(step) && step.on_failure) return [["fallback", step.on_failure.steps]];
  return [];
}

/** `step` with the list at `arm` replaced. */
function withArm(step: WorkflowStep, arm: Arm, next: WorkflowStep[]): WorkflowStep {
  if (arm === "fallback" && canRecover(step) && step.on_failure) {
    return { ...step, on_failure: { ...step.on_failure, steps: next } };
  }
  if (step.kind === "choice" && arm.startsWith("case:")) {
    const at = Number(arm.slice(5));
    return { ...step, cases: step.cases.map((c, i) => (i === at ? { ...c, steps: next } : c)) };
  }
  return { ...step, [arm]: next } as WorkflowStep;
}

/** `step` with each list it holds replaced by `change`'s. */
export function withChildren(
  step: WorkflowStep,
  change: (arm: Arm, list: WorkflowStep[]) => WorkflowStep[],
): WorkflowStep {
  let next: WorkflowStep = step;
  for (const [arm, list] of childLists(step)) next = withArm(next, arm, change(arm, list));
  return next;
}

/** `step` with every list it holds passed through `change`. */
function mapArms(step: WorkflowStep, change: (list: WorkflowStep[]) => WorkflowStep[]): WorkflowStep {
  let next: WorkflowStep = step;
  for (const [arm, list] of childLists(step)) next = withArm(next, arm, change(list));
  return next;
}

export interface PlacedStep {
  /** Document order, nested steps included -- the number the server's
   * messages and the run view use. */
  number: number;
  step: WorkflowStep;
  list: ListRef;
  index: number;
  depth: number;
  /** Ids of the loops around the step, outermost first. */
  loops: string[];
}

export function placeSteps(steps: WorkflowStep[]): PlacedStep[] {
  const placed: PlacedStep[] = [];
  const visit = (items: WorkflowStep[], list: ListRef, depth: number, loops: string[]) => {
    items.forEach((step, index) => {
      placed.push({ number: placed.length + 1, step, list, index, depth, loops });
      const inner = step.kind === "loop" ? [...loops, step.id] : loops;
      for (const [arm, children] of childLists(step)) visit(children, { parent: step.id, arm }, depth + 1, inner);
    });
  };
  visit(steps, ROOT, 0, []);
  return placed;
}

export function allSteps(workflow: Workflow): WorkflowStep[] {
  return placeSteps(everyStep(workflow)).map((placed) => placed.step);
}

/** How many steps a block holds, all the way down. */
export function countInside(step: WorkflowStep): number {
  return placeSteps([step]).length - 1;
}

export function listAt(workflow: Workflow, ref: ListRef): WorkflowStep[] {
  if (ref.parent === null) return ref.arm === "after_failure" ? (workflow.after_failure ?? []) : workflow.steps;
  const parent = allSteps(workflow).find((step) => step.id === ref.parent);
  const found = parent ? childLists(parent).find(([arm]) => arm === ref.arm) : undefined;
  return found ? found[1] : [];
}

function replaceList(steps: WorkflowStep[], ref: ListRef, next: WorkflowStep[]): WorkflowStep[] {
  return steps.map((step) => {
    if (step.id === ref.parent && ref.arm) return withArm(step, ref.arm, next);
    return mapArms(step, (list) => replaceList(list, ref, next));
  });
}

export function withList(workflow: Workflow, ref: ListRef, next: WorkflowStep[]): Workflow {
  if (ref.parent === null) {
    return ref.arm === "after_failure" ? { ...workflow, after_failure: next } : { ...workflow, steps: next };
  }
  const after = workflow.after_failure;
  return {
    ...workflow,
    steps: replaceList(workflow.steps, ref, next),
    ...(after ? { after_failure: replaceList(after, ref, next) } : {}),
  };
}

/** Applies `change` to every step, children first. */
function mapSteps(steps: WorkflowStep[], change: (step: WorkflowStep) => WorkflowStep): WorkflowStep[] {
  return steps.map((step) => change(mapArms(step, (list) => mapSteps(list, change))));
}

/** The workflow with `change` applied to every step, those after a failed run too. */
export function mapWorkflow(workflow: Workflow, change: (step: WorkflowStep) => WorkflowStep): Workflow {
  const after = workflow.after_failure;
  return {
    ...workflow,
    steps: mapSteps(workflow.steps, change),
    ...(after ? { after_failure: mapSteps(after, change) } : {}),
  };
}

// -- What a step can read -------------------------------------------------------

function outputNames(step: WorkflowStep): string[] {
  if (step.kind === "llm") return [step.save_as, ...step.fields.map((field) => `${step.save_as}.${field.name}`)];
  if (step.kind === "agent" && step.save_as) {
    // workflow_spec/spec.py's AgentStep.result_fields.
    const fields = step.fields.length > 0 ? step.fields.map((field) => field.name) : ["report"];
    return [step.save_as, ...fields.map((field) => `${step.save_as}.${field}`)];
  }
  const output = "save_as" in step ? step.save_as : null;
  return output ? [output] : [];
}

/** What the steps that run because a step failed read about it (workflow_spec's FAILURE). */
const FAILURE_NAMES = ["failure", "failure.step", "failure.message"];

/** Names readable at each position of each list ("<listKey>#<index>"),
 * scoped like workflow_spec/scope.py: a loop's item and body results only
 * inside it, a branch's or choice's results after it only when every path makes them,
 * a step's result after it only when a failure can't skip it.
 * Model steps' fields are listed too, for pickers. */
export function scopes(workflow: Workflow): Map<string, string[]> {
  const at = new Map<string, string[]>();
  const check = (steps: WorkflowStep[], ref: ListRef, available: string[]): string[] => {
    let names = [...available];
    steps.forEach((step, index) => {
      at.set(`${listKey(ref)}#${index}`, names);
      if (step.kind === "branch" || step.kind === "choice") {
        // A name made on every path is there after the block; one made on some paths isn't.
        const after = childLists(step).map(([arm, list]) => check(list, { parent: step.id, arm }, names));
        const everywhere = after[0].filter((name) => !names.includes(name) && after.every((a) => a.includes(name)));
        names = [...names, ...everywhere];
        return;
      }
      if (step.kind === "loop") check(step.steps, { parent: step.id, arm: "steps" }, [...names, step.item]);
      const then = canRecover(step) ? step.on_failure?.then : undefined;
      if (then === "skip") return;
      if (then === "steps" && canRecover(step) && step.on_failure) {
        const inPlace = { parent: step.id, arm: "fallback" as const };
        const made = check(step.on_failure.steps, inPlace, [...names, ...FAILURE_NAMES]);
        names = [...names, ...outputNames(step).filter((name) => made.includes(name))];
        return;
      }
      names = [...names, ...outputNames(step)];
    });
    at.set(`${listKey(ref)}#${steps.length}`, names);
    return names;
  };
  const memory = workflow.memory?.length
    ? [...workflow.memory.map((m) => `memory.${m.name}`), "run.started_at", "run.date"]
    : [];
  const inputs = [...workflow.inputs.map((input) => input.name), ...memory];
  check(workflow.steps, ROOT, inputs);
  check(workflow.after_failure ?? [], AFTER_FAILURE, [...inputs, ...FAILURE_NAMES]);
  return at;
}

export function scopeAt(scopeMap: Map<string, string[]>, ref: ListRef, index: number): string[] {
  return scopeMap.get(`${listKey(ref)}#${index}`) ?? [];
}
