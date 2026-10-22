/** Comments left on the plan under review: a quoted passage and what the
 * person wants changed in it. They wait here until Revise sends them to the
 * model inside its feedback. Kept by plan text, so a new plan starts with none. */

import { useSyncExternalStore } from "react";

export interface PlanComment {
  id: string;
  /** The words the comment is about, as selected in the plan. */
  quote: string;
  text: string;
}

const NONE: PlanComment[] = [];
const byPlan = new Map<string, PlanComment[]>();
const listeners = new Set<() => void>();

export function commentsOf(plan: string | null): PlanComment[] {
  return (plan !== null && byPlan.get(plan)) || NONE;
}

export function setPlanComments(plan: string, comments: PlanComment[]): void {
  if (comments.length === 0) byPlan.delete(plan);
  else byPlan.set(plan, comments);
  listeners.forEach((listener) => listener());
}

export function usePlanComments(plan: string | null): PlanComment[] {
  return useSyncExternalStore(
    (listener) => {
      listeners.add(listener);
      return () => listeners.delete(listener);
    },
    () => commentsOf(plan),
  );
}

/** The selected words as a one-line quote. */
export function quoteOf(selected: string): string {
  return selected.replace(/\s+/g, " ").trim();
}

/** What Revise sends: the person's own words, then each comment under the
 * passage it is about. The comments are spent once they are sent. */
export function withPlanComments(plan: string, feedback: string): string {
  const comments = commentsOf(plan);
  if (comments.length === 0) return feedback;
  setPlanComments(plan, []);
  const listed = comments.map((comment) => `> ${comment.quote}\n${comment.text}`).join("\n\n");
  return `${feedback.trim() ? `${feedback.trim()}\n\n` : ""}Comments on the plan:\n\n${listed}`;
}
