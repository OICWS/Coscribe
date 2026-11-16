/** The task list of a plan under review, as the person is editing it in the Plan panel. Kept by
 * the plan's id until they answer the plan: Accept sends the edited list with the answer and the
 * server makes it the plan's list (conversation/approvals.py, TaskToolkit.replace). */

import { useSyncExternalStore } from "react";
import type { PlanTaskEdit } from "../types/wire.gen";
import type { ProgressItem } from "./workflowProgress";

export interface DraftStep {
  /** Stable across edits, for React and focus; a new step has no task id. */
  key: string;
  id?: string;
  content: string;
  /** Unticked: left out of the plan. */
  included: boolean;
}

interface Draft {
  /** The list the model wrote, to tell an edit from no edit. */
  base: ProgressItem[];
  steps: DraftStep[];
}

const byPlan = new Map<string, Draft>();
const listeners = new Set<() => void>();
const notify = () => listeners.forEach((listener) => listener());

export function stepsOf(tasks: ProgressItem[]): DraftStep[] {
  return tasks.map((task) => ({ key: `task-${task.id}`, id: task.id, content: task.content, included: true }));
}

/** The draft of a plan, or null while the person has not touched its list. */
export function planTaskDraftOf(planId: string | null): Draft | null {
  return (planId !== null && byPlan.get(planId)) || null;
}

export function setPlanTaskDraft(planId: string, base: ProgressItem[], steps: DraftStep[]): void {
  byPlan.set(planId, { base, steps });
  notify();
}

export function usePlanTaskDraft(planId: string | null): Draft | null {
  return useSyncExternalStore(
    (listener) => {
      listeners.add(listener);
      return () => listeners.delete(listener);
    },
    () => planTaskDraftOf(planId),
  );
}

/** What the answer to the plan carries: the steps kept, in order; undefined when the list is
 * the one the model wrote. */
export function draftEdits(planId: string): PlanTaskEdit[] | undefined {
  const draft = planTaskDraftOf(planId);
  if (!draft) return undefined;
  const kept = draft.steps
    .filter((step) => step.included && step.content.trim() !== "")
    .map((step) => (step.id === undefined ? { content: step.content.trim() } : { id: step.id, content: step.content.trim() }));
  const unchanged =
    kept.length === draft.base.length && kept.every((step, i) => step.id === draft.base[i].id && step.content === draft.base[i].content);
  return unchanged ? undefined : kept;
}

/** The plan's answer was sent: its draft is spent. */
export function forgetPlanTaskDraft(planId: string): void {
  if (byPlan.delete(planId)) notify();
}

/** The list the server makes of `edits` (TaskToolkit.replace): a kept id keeps its status, a new
 * step is numbered past every old id. The live turn sends no result for exit_plan_mode, so the
 * Plan panel shows this until a replayed history brings the server's own list. */
export function approvedList(base: ProgressItem[], edits: PlanTaskEdit[]): ProgressItem[] {
  const byId = new Map(base.map((task) => [task.id, task]));
  let next = Math.max(0, ...base.map((task) => Number(task.id)).filter(Number.isFinite)) + 1;
  return edits.map((edit) => {
    const old = edit.id === undefined ? undefined : byId.get(edit.id);
    if (old) {
      byId.delete(old.id);
      return { ...old, content: edit.content };
    }
    return { id: String(next++), content: edit.content, status: "pending" };
  });
}
