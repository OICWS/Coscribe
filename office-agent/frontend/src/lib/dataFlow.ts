import type { Condition, Workflow, WorkflowStep } from "../types/workflow";
import { operandReference, splitTemplate, stepOutput } from "./workflowLabels";
import { everyStep, placeSteps } from "./workflowTree";

// Which values each step reads and which steps read what it makes, for highlighting a step's
// data on the canvas. Mirrors workflow_spec's step_references; names are the part before the
// first dot.

function textReads(text: string): string[] {
  return splitTemplate(text).flatMap((part) => ("ref" in part ? [part.ref] : []));
}

function valueReads(value: unknown): string[] {
  if (typeof value === "string") return textReads(value);
  if (Array.isArray(value)) return value.flatMap(valueReads);
  if (value && typeof value === "object") return Object.values(value).flatMap(valueReads);
  return [];
}

function conditionReads(conditions: Condition[]): string[] {
  return conditions
    .flatMap((c) => [c.left, ...(c.right ? [c.right] : [])].map(operandReference))
    .filter((ref): ref is string => ref !== null);
}

function readsOf(step: WorkflowStep): string[] {
  switch (step.kind) {
    case "tool":
      return valueReads(step.args);
    case "script":
    case "run_task":
      return valueReads(step.inputs);
    case "llm":
      return textReads(step.prompt);
    case "agent":
      return textReads(step.goal);
    case "check":
    case "branch":
      return conditionReads(step.conditions);
    case "approval":
      return [...textReads(step.message), ...conditionReads(step.when)];
    case "ask":
      return [...textReads(step.message), ...step.fields.flatMap((f) => (f.items ? [f.items] : []))];
    case "wait":
      return [...textReads(step.path ?? ""), ...textReads(step.on ?? "")];
    case "remember":
      return textReads(step.value);
    case "choice":
      return [step.value];
    case "parallel":
      return [];
    case "loop":
      return [step.over, ...(step.collect ? [step.collect] : []), ...conditionReads(step.until ?? [])];
  }
}

export interface StepFlow {
  /** Steps whose results it reads. */
  from: Set<string>;
  /** Inputs it reads, by name. */
  inputs: Set<string>;
  /** Steps that read what it makes. */
  to: Set<string>;
}

/** Each step's data links. A name made in several places (each arm of a branch, a step and the
 * steps in its place) links to every one of them. */
export function dataFlow(workflow: Workflow): Map<string, StepFlow> {
  const placed = placeSteps(everyStep(workflow));
  const makers = new Map<string, string[]>();
  const make = (name: string, id: string) => makers.set(name, [...(makers.get(name) ?? []), id]);
  for (const { step } of placed) {
    const output = stepOutput(step);
    if (output) make(output, step.id);
    if (step.kind === "loop") make(step.item, step.id);
  }
  const inputs = new Set(workflow.inputs.map((input) => input.name));
  const flows = new Map<string, StepFlow>(
    placed.map(({ step }) => [step.id, { from: new Set(), inputs: new Set(), to: new Set() }]),
  );
  for (const { step } of placed) {
    const flow = flows.get(step.id)!;
    for (const name of readsOf(step).map((ref) => ref.split(".")[0])) {
      if (inputs.has(name)) flow.inputs.add(name);
      for (const maker of makers.get(name) ?? []) {
        if (maker === step.id) continue;
        flow.from.add(maker);
        flows.get(maker)!.to.add(step.id);
      }
    }
  }
  return flows;
}

/** How a step relates to the one in focus. */
export type FlowRole = "focus" | "feeds" | "uses" | "both" | "other";

export function flowRole(flows: Map<string, StepFlow>, focus: string, stepId: string): FlowRole {
  if (stepId === focus) return "focus";
  const flow = flows.get(focus);
  const feeds = flow?.from.has(stepId) ?? false;
  const uses = flow?.to.has(stepId) ?? false;
  return feeds && uses ? "both" : feeds ? "feeds" : uses ? "uses" : "other";
}
