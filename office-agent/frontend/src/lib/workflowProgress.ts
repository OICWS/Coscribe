import type { ScheduledRun } from "../types/settings";
import type { LoopStep, StepRecord, StepStatus, Workflow, WorkflowStep } from "../types/workflow";
import { RUN_STATUS_LABEL } from "./runLabels";
import { childLists, everyStep, isBlock, placeSteps } from "./workflowTree";

export type ProgressStatus = "pending" | "in_progress" | "completed" | "failed";

export interface ProgressItem {
  id: string;
  content: string;
  status: ProgressStatus;
}

// -- Records ----------------------------------------------------------------------

/** A step's record is one per pass of the loops around it. */
export function recordKey(stepId: string, iteration: number[] = []): string {
  return `${stepId}@${iteration.join(".")}`;
}

export function recordMap(run: ScheduledRun): Map<string, StepRecord> {
  return new Map(run.steps.map((record) => [recordKey(record.step_id, record.iteration), record]));
}

export interface LoopProgress {
  done: number;
  total: number;
  /** A short name per item, in order. */
  items: string[];
  collected?: unknown;
  /** Items a failure skipped (decision 0032), in order. */
  skipped: SkippedItem[];
}

interface SkippedItem {
  index: number;
  label: string;
  error: string;
}

export function loopProgress(record: StepRecord | undefined): LoopProgress | null {
  const output = record?.output;
  if (typeof output !== "object" || output === null || !("total" in output)) return null;
  const { done, total, items, collected, skipped } = output as Record<string, unknown>;
  return {
    done: typeof done === "number" ? done : 0,
    total: typeof total === "number" ? total : 0,
    items: Array.isArray(items) ? items.map(String) : [],
    collected,
    skipped: Array.isArray(skipped) ? (skipped as SkippedItem[]) : [],
  };
}

function descendants(step: WorkflowStep): WorkflowStep[] {
  return placeSteps([step])
    .slice(1)
    .map((placed) => placed.step);
}

/** How one pass of a loop went, from the records of the steps inside it. */
export function passStatus(
  loop: LoopStep,
  path: number[],
  records: Map<string, StepRecord>,
): StepStatus | "not_reached" | "recovered" {
  const statuses: (StepStatus | "recovered")[] = [];
  for (const placed of placeSteps(loop.steps)) {
    // Only the steps directly in this pass; deeper loops add their own index.
    const depth = placed.loops.length;
    const record = depth === 0 ? records.get(recordKey(placed.step.id, path)) : undefined;
    if (record) statuses.push(record.status === "failed" && record.recovered ? "recovered" : record.status);
  }
  if (statuses.length === 0) return "not_reached";
  for (const status of ["failed", "waiting", "running", "recovered"] as const) {
    if (statuses.includes(status)) return status;
  }
  return "done";
}

/** A block whose own record says failed or waiting because of a step
 * inside it -- that step shows the problem, not the block. */
export function stoppedInside(step: WorkflowStep, run: ScheduledRun): boolean {
  // A step that ran another task holds that task's records, as "<step>/<its step>" (decision 0035).
  const ran = step.kind === "run_task";
  if (!ran && !isBlock(step)) return false;
  const inside = new Set(ran ? [] : descendants(step).map((s) => s.id));
  const within = (id: string) => (ran ? id.startsWith(`${step.id}/`) : inside.has(id));
  return run.steps.some(
    (r) => within(r.step_id) && ((r.status === "failed" && !r.recovered) || r.status === "waiting"),
  );
}

// -- Side panel and header ----------------------------------------------------------

function progressOf(record: StepRecord | undefined, runGoing: boolean): ProgressStatus {
  const status = record?.status;
  // A failure the step's own setting handled (decision 0032) let the run go on.
  if (status === "done" || status === "skipped" || record?.recovered) return "completed";
  // A stopped run leaves its last step's record at "running".
  if (status === "running") return runGoing ? "in_progress" : "pending";
  if (status === "waiting") return "in_progress";
  if (status === "failed") return "failed";
  return "pending";
}

/** A workflow run as the side panel's progress row: one entry per step
 * that runs once -- a loop is one entry counting its items, and only the
 * arm a branch took is listed. */
export function workflowProgress(workflow: Workflow, run: ScheduledRun): ProgressItem[] {
  const records = recordMap(run);
  const going = run.status === "running";
  const items: ProgressItem[] = [];
  const visit = (steps: WorkflowStep[]) => {
    for (const step of steps) {
      const record = records.get(recordKey(step.id));
      if (step.kind === "loop") {
        const progress = loopProgress(record);
        const skipped = progress?.skipped.length ? ` · ${progress.skipped.length} skipped` : "";
        const counted = progress ? ` · ${progress.done} of ${progress.total}${skipped}` : "";
        items.push({ id: step.id, content: `${step.title}${counted}`, status: progressOf(record, going) });
        continue;
      }
      const note =
        record?.recovered === "skipped" ? " · skipped" : record?.recovered === "fallback" ? " · replaced" : "";
      // A step that ran another task, or runs lanes, stays "running" while a step inside waits.
      const holds = step.kind === "run_task" || step.kind === "parallel";
      const asking = holds && record?.status === "running" && stoppedInside(step, run);
      items.push({
        id: step.id,
        content: `${step.title}${note}`,
        status: asking ? "in_progress" : progressOf(record, going),
      });
      if (record?.recovered === "fallback") visit(childLists(step).find(([a]) => a === "fallback")?.[1] ?? []);
      if (step.kind === "parallel" && record) step.lanes.forEach((lane) => visit(lane.steps));
      if ((step.kind === "branch" || step.kind === "choice") && record?.status === "done") {
        const arm = (record.output as { arm?: string } | null)?.arm;
        visit(childLists(step).find(([a]) => a === arm)?.[1] ?? []);
      }
    }
  };
  visit(workflow.steps);
  return items;
}

/** The run header's status, naming the step when it matters. */
export function workflowRunLabel(workflow: Workflow, run: ScheduledRun): string | null {
  const placed = placeSteps(everyStep(workflow));
  const where = (status: StepStatus) => {
    const record = [...run.steps]
      .reverse()
      .find(
        (r) => r.status === status && !r.recovered && !placed.find((p) => p.step.id === r.step_id && isBlock(p.step)),
      );
    const spot = record ? placed.find((p) => p.step.id === record.step_id) : undefined;
    if (!record || !spot) return null;
    const pass = record.iteration?.length ? `, item ${record.iteration[record.iteration.length - 1] + 1}` : "";
    return `step ${spot.number}${pass}`;
  };
  if (run.status === "failed") {
    const at = where("failed");
    return at ? `Failed at ${at}` : "Failed";
  }
  if (run.status === "stopped") {
    const at = where("running");
    return at ? `Stopped at ${at}` : null;
  }
  if (run.status === "needs_approval" || run.status === "waiting") {
    const at = where("waiting");
    return at ? `Waiting at ${at}` : RUN_STATUS_LABEL[run.status];
  }
  return null;
}
