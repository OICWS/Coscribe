import type { ScheduledRun } from "../types/settings";
import type { Workflow, WorkflowStep } from "../types/workflow";
import { everyStep, mapWorkflow, placeSteps } from "./workflowTree";

// A step that ran another task (decision 0035) keeps that task's records as "<step>/<its step>":
// the called task's steps, renamed the same way, are what those records belong to.

/** The task `stepId` ran, as the run found it, with step ids as its records name them. */
export function calledWorkflow(run: ScheduledRun, stepId: string): Workflow | null {
  const called = run.called?.[stepId];
  if (!called) return null;
  return mapWorkflow(called.workflow, (step: WorkflowStep) => ({ ...step, id: `${stepId}/${step.id}` }));
}

const ADDED = /^(.+)\/added\/(.+)$/;

/** A step the run added because one failed (decision 0042), or the approval in front of it: its
 * title is on the failed step's record, under the id its own records carry after `/added/`. */
function addedStepTitle(run: ScheduledRun, stepId: string): string | null {
  const match = ADDED.exec(stepId);
  if (!match) return null;
  const [, owner, id] = match;
  const plan = run.steps.find((record) => record.step_id === owner && record.agent?.added)?.agent?.added;
  const own = id.startsWith("before_") ? id.slice("before_".length) : id;
  const title = plan?.steps.find((step) => step.id === own)?.title;
  if (typeof title !== "string") return null;
  return own === id ? `${title} (added by the run)` : `Before “${title}” (added by the run)`;
}

/** A step's title anywhere in the run, a called task's steps and the steps it added too. */
export function runStepTitle(workflow: Workflow, run: ScheduledRun, stepId: string | undefined): string {
  if (!stepId) return "a step";
  const added = addedStepTitle(run, stepId);
  if (added) return added;
  const cut = stepId.lastIndexOf("/");
  const owner = cut < 0 ? workflow : calledWorkflow(run, stepId.slice(0, cut));
  const steps = owner ? everyStep(owner) : [];
  const title = placeSteps(steps).find((placed) => placed.step.id === stepId)?.step.title;
  const task = cut < 0 ? null : run.called?.[stepId.slice(0, cut)]?.name;
  return title ? (task ? `${title} (in “${task}”)` : title) : stepId;
}

/** A run-task step's own record stays "running" while a step of its task waits. */
export function waitingInside(stepId: string, run: ScheduledRun): boolean {
  return run.steps.some((record) => record.step_id.startsWith(`${stepId}/`) && record.status === "waiting");
}
