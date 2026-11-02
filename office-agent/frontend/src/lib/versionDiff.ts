import type { Workflow, WorkflowStep } from "../types/workflow";
import { allSteps } from "./workflowTree";

/** How a step differs between two versions of a task's workflow (decision 0035), by its id. */
interface StepChange {
  id: string;
  title: string;
  change: "added" | "removed" | "changed";
}

export interface VersionDiff {
  steps: StepChange[];
  /** Labels of the inputs added, removed or changed. */
  inputs: string[];
  /** Whether what the task remembers, its steps after a failure or its autonomy changed. */
  otherwise: string[];
}

// A block's own settings, not the steps it holds: those are compared one by one.
const HELD = new Set(["then", "otherwise", "steps"]);

function ownPart(step: WorkflowStep): string {
  return JSON.stringify(step, (key, value: unknown) => (HELD.has(key) && Array.isArray(value) ? undefined : value));
}

/** What changed from `older` to `newer`, in `newer`'s order, then what `older` had that is gone. */
export function compareVersions(older: Workflow, newer: Workflow): VersionDiff {
  const before = new Map(allSteps(older).map((step) => [step.id, step]));
  const after = allSteps(newer);
  const steps: StepChange[] = [];
  for (const step of after) {
    const was = before.get(step.id);
    if (!was) steps.push({ id: step.id, title: step.title, change: "added" });
    else if (ownPart(was) !== ownPart(step)) steps.push({ id: step.id, title: step.title, change: "changed" });
  }
  const kept = new Set(after.map((step) => step.id));
  for (const [id, step] of before) if (!kept.has(id)) steps.push({ id, title: step.title, change: "removed" });
  const inputsBefore = new Map(older.inputs.map((input) => [input.name, JSON.stringify(input)]));
  const inputsAfter = new Map(newer.inputs.map((input) => [input.name, JSON.stringify(input)]));
  const inputs = [...new Set([...inputsBefore.keys(), ...inputsAfter.keys()])]
    .filter((name) => inputsBefore.get(name) !== inputsAfter.get(name))
    .map((name) => [...older.inputs, ...newer.inputs].find((input) => input.name === name)?.label || name);
  const otherwise = [
    JSON.stringify(older.memory ?? []) !== JSON.stringify(newer.memory ?? []) ? "what it remembers" : "",
    (older.autonomy ?? null) !== (newer.autonomy ?? null) ? "its autonomy" : "",
  ].filter(Boolean);
  return { steps, inputs, otherwise };
}

export const VERSION_HOW: Record<string, string> = {
  created: "Created",
  edited: "Edited",
  conversation: "Saved from a conversation",
  restored: "Restored",
  found: "As it was before versions were kept",
};
