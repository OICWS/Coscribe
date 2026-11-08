import type { OutputField, Workflow, WorkflowInput, WorkflowStep } from "../types/workflow";
import { listWords, plainConditions, plainDetail, plainReference } from "./plainSteps";

// What a task does, as the simple view lists it: each step by its own title and one sentence,
// a block's steps under the words that say when they run. Nothing here names a tool, a field or
// a variable.

export interface PlainGroup {
  /** "Otherwise", a lane's name; null where the block's own sentence already says it. */
  label: string | null;
  rows: PlainRow[];
}

export interface PlainRow {
  step: WorkflowStep;
  detail: string | null;
  /** Said only when the step was set to: what happens when it fails, that it can't be undone. */
  notes: string[];
  groups: PlainGroup[];
}

function words(name: string): string {
  return name.replace(/_/g, " ");
}

/** "Works out urgent tickets and longest wait": what a model step hands on. */
function worksOut(fields: OutputField[]): string | null {
  if (fields.length === 0) return null;
  // A short description ("Urgent tickets") says it better than a name like "count".
  const named = fields.map((field) => {
    const said = field.description.trim();
    return said && said.length <= 30 ? said[0].toLowerCase() + said.slice(1) : words(field.name);
  });
  const shown = named.length > 3 ? [...named.slice(0, 3), `${named.length - 3} more`] : named;
  return `Works out ${listWords(shown)}`;
}

function detail(step: WorkflowStep, inputs: WorkflowInput[], ctx: OutlineContext): string | null {
  switch (step.kind) {
    case "llm":
      return worksOut(step.fields) ?? plainDetail(step, inputs);
    case "agent":
      return worksOut(step.fields) ?? plainDetail(step, inputs);
    case "branch": {
      const when = plainConditions(step.conditions, step.match, inputs);
      return when ? `If ${when}` : null;
    }
    case "choice":
      return `Depending on ${plainReference(step.value, inputs)}`;
    case "loop":
      return `For each ${words(step.item)} in ${plainReference(step.over, inputs)}`;
    case "parallel":
      return "At the same time";
    default:
      return plainDetail(step, inputs, ctx.workflow.memory ?? [], ctx.taskNames);
  }
}

function notes(step: WorkflowStep): string[] {
  const said: string[] = [];
  if ("irreversible" in step && step.irreversible) said.push("Can’t be undone");
  const failure = "on_failure" in step ? step.on_failure : null;
  if (failure?.retries) said.push(`Tries again up to ${failure.retries === 1 ? "once" : `${failure.retries} times`}`);
  if (failure?.then === "skip") said.push("Skipped if it fails");
  return said;
}

function groups(step: WorkflowStep, ctx: OutlineContext): PlainGroup[] {
  const of = (label: string | null, steps: WorkflowStep[]) => ({ label, rows: rows(steps, ctx) });
  const all: PlainGroup[] = [];
  if (step.kind === "branch") all.push(of(null, step.then), of("Otherwise", step.otherwise));
  if (step.kind === "choice") {
    for (const path of step.cases) all.push(of(`When it is “${path.is}”`, path.steps));
    all.push(of("Otherwise", step.otherwise));
  }
  if (step.kind === "loop") all.push(of(null, step.steps));
  if (step.kind === "parallel") for (const lane of step.lanes) all.push(of(lane.label, lane.steps));
  const failure = "on_failure" in step ? step.on_failure : null;
  if (failure?.then === "steps") all.push(of("If it fails", failure.steps));
  return all.filter((group) => group.rows.length > 0);
}

interface OutlineContext {
  workflow: Workflow;
  taskNames: Map<string, string>;
}

function rows(steps: WorkflowStep[], ctx: OutlineContext): PlainRow[] {
  return steps.map((step) => ({
    step,
    detail: detail(step, ctx.workflow.inputs, ctx),
    notes: notes(step),
    groups: groups(step, ctx),
  }));
}

/** The task's steps as the simple view lists them. `taskNames`: saved tasks by id (decision 0035). */
export function plainOutline(workflow: Workflow, taskNames: Map<string, string> = new Map()): PlainRow[] {
  return rows(workflow.steps, { workflow, taskNames });
}

/** What a run stops to ask the person: each step that waits for their OK or their answer. */
export function waitsForYou(workflow: Workflow): WorkflowStep[] {
  const found: WorkflowStep[] = [];
  const visit = (row: PlainRow) => {
    if (row.step.kind === "approval" || row.step.kind === "ask") found.push(row.step);
    row.groups.forEach((group) => group.rows.forEach(visit));
  };
  plainOutline(workflow).forEach(visit);
  return found;
}
