import type { BlockStep, Workflow, WorkflowStep } from "../types/workflow";

// Branches and loops hold their own step lists. A list is named by the
// block that holds it and which of its lists it is; ids are unique across
// the whole workflow, so that's enough to find it.

/** A choice's paths are "case:0", "case:1"..., then "otherwise". */
export type Arm = "then" | "otherwise" | "steps" | `case:${number}`;

export interface ListRef {
  parent: string | null;
  arm: Arm | null;
}

export const ROOT: ListRef = { parent: null, arm: null };

export function listKey(ref: ListRef): string {
  return ref.parent === null ? "root" : `${ref.parent}:${ref.arm}`;
}

export function isBlock(step: WorkflowStep): step is BlockStep {
  return step.kind === "branch" || step.kind === "choice" || step.kind === "loop";
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
  return [];
}

/** `step` with the list at `arm` replaced. */
function withArm(step: BlockStep, arm: Arm, next: WorkflowStep[]): WorkflowStep {
  if (step.kind === "choice" && arm.startsWith("case:")) {
    const at = Number(arm.slice(5));
    return { ...step, cases: step.cases.map((c, i) => (i === at ? { ...c, steps: next } : c)) };
  }
  return { ...step, [arm]: next } as WorkflowStep;
}

/** `step` with every list it holds passed through `change`. */
function mapArms(step: BlockStep, change: (list: WorkflowStep[]) => WorkflowStep[]): WorkflowStep {
  let next: WorkflowStep = step;
  for (const [arm, list] of childLists(step)) next = withArm(next as BlockStep, arm, change(list));
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
  return placeSteps(workflow.steps).map((placed) => placed.step);
}

/** How many steps a block holds, all the way down. */
export function countInside(step: WorkflowStep): number {
  return placeSteps([step]).length - 1;
}

export function listAt(workflow: Workflow, ref: ListRef): WorkflowStep[] {
  if (ref.parent === null) return workflow.steps;
  const parent = allSteps(workflow).find((step) => step.id === ref.parent);
  const found = parent ? childLists(parent).find(([arm]) => arm === ref.arm) : undefined;
  return found ? found[1] : [];
}

function replaceList(steps: WorkflowStep[], ref: ListRef, next: WorkflowStep[]): WorkflowStep[] {
  return steps.map((step) => {
    if (!isBlock(step)) return step;
    if (step.id === ref.parent && ref.arm) return withArm(step, ref.arm, next);
    return mapArms(step, (list) => replaceList(list, ref, next));
  });
}

export function withList(workflow: Workflow, ref: ListRef, next: WorkflowStep[]): Workflow {
  if (ref.parent === null) return { ...workflow, steps: next };
  return { ...workflow, steps: replaceList(workflow.steps, ref, next) };
}

/** Applies `change` to every step, children first. */
export function mapSteps(steps: WorkflowStep[], change: (step: WorkflowStep) => WorkflowStep): WorkflowStep[] {
  return steps.map((step) => change(isBlock(step) ? mapArms(step, (list) => mapSteps(list, change)) : step));
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

/** Names readable at each position of each list ("<listKey>#<index>"),
 * scoped like workflow_spec/spec.py: a loop's item and body results only
 * inside it, a branch's or choice's results after it only when every path makes them.
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
      names = [...names, ...outputNames(step)];
    });
    at.set(`${listKey(ref)}#${steps.length}`, names);
    return names;
  };
  check(
    workflow.steps,
    ROOT,
    workflow.inputs.map((input) => input.name),
  );
  return at;
}

export function scopeAt(scopeMap: Map<string, string[]>, ref: ListRef, index: number): string[] {
  return scopeMap.get(`${listKey(ref)}#${index}`) ?? [];
}
