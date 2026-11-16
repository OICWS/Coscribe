/** The conversation's plan as App wires it: what the Plan panel shows (in the dock or a window
 * of its own), the comments and task-list edits waiting for the answer, and the answer itself. */

import { useEffect, type Dispatch } from "react";
import type { ChatAction, LogItem } from "../state/reducer";
import type { WsClientMessage } from "../types/wire";
import { setPlanComments, usePlanComments, withPlanComments, type PlanComment } from "./planComments";
import {
  approvedList,
  draftEdits,
  forgetPlanTaskDraft,
  planTaskDraftOf,
  setPlanTaskDraft,
  stepsOf,
  usePlanTaskDraft,
  type DraftStep,
} from "./planTaskDraft";
import { planPanelData } from "./taskCard";

export type PlanItem = Extract<LogItem, { kind: "plan" }>;
export type PlanChoice = "auto" | "manual" | "revise" | "reject";

/** The plan's title: its first heading, else its first line. */
export function planTitleOf(plan: string): string {
  const lines = plan.split("\n").map((line) => line.trim()).filter(Boolean);
  const heading = lines.find((line) => /^#{1,6}\s/.test(line));
  return (heading ?? lines[0] ?? "").replace(/^#{1,6}\s+/, "").replace(/[*_`]/g, "");
}

export type PlanPanelAction =
  | { type: "planComments"; plan: string; comments: PlanComment[] }
  | { type: "planSteps"; planId: string; steps: DraftStep[] };

export function usePlanState(
  items: LogItem[],
  send: (message: WsClientMessage) => void,
  dispatch: Dispatch<ChatAction>,
  openPanel: () => void,
) {
  const { tasks, plan, pendingPlanId } = planPanelData(items);
  const comments = usePlanComments(plan);
  const draft = usePlanTaskDraft(pendingPlanId);
  const steps = pendingPlanId === null ? null : (draft?.steps ?? stepsOf(tasks));

  // A plan waiting for an answer is read and edited in the panel, so it opens with the plan.
  useEffect(() => {
    if (pendingPlanId !== null) openPanel();
    // eslint-disable-next-line react-hooks/exhaustive-deps -- once per new plan, not per render
  }, [pendingPlanId]);

  const onPanelAction = (action: PlanPanelAction) => {
    if (action.type === "planComments") setPlanComments(action.plan, action.comments);
    else setPlanTaskDraft(action.planId, planTaskDraftOf(action.planId)?.base ?? tasks, action.steps);
  };

  const answer = (item: PlanItem, choice: PlanChoice, feedback: string) => {
    const edits = choice === "reject" ? undefined : draftEdits(item.id);
    const base = planTaskDraftOf(item.id)?.base ?? tasks;
    forgetPlanTaskDraft(item.id);
    const approved = edits && choice !== "revise" ? approvedList(base, edits) : undefined;
    dispatch({ type: "local_plan_answered", id: item.id, status: choice, ...(approved ? { tasks: approved } : {}) });
    send({
      type: "question_response",
      id: item.id,
      answer: choice === "revise" ? `revise:${withPlanComments(item.plan, feedback)}` : choice,
      ...(edits ? { tasks: edits } : {}),
    });
  };

  const review = pendingPlanId !== null && steps !== null ? { planId: pendingPlanId, steps } : null;
  return {
    hasPlan: tasks.length > 0,
    answer,
    onPanelAction,
    /** What a Plan panel in its own window is sent. */
    panelState: { tasks, plan, comments, review },
    /** The docked Plan panel's props. */
    panelProps: {
      tasks,
      plan,
      comments,
      onComments: (next: PlanComment[]) => setPlanComments(plan ?? "", next),
      review: review && { steps: review.steps, onSteps: (next: DraftStep[]) => onPanelAction({ type: "planSteps", planId: review.planId, steps: next }) },
    },
  };
}
