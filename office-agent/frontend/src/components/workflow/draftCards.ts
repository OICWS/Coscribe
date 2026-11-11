import { createContext } from "react";
import type { DraftTest, WorkflowDraftEntry, WorkflowTestResult } from "../../lib/transcriptGrouping";
import { placeSteps } from "../../lib/workflowTree";

/** What every draft card in a conversation shares: the tests run on the
 * drafts, which were saved, and what the buttons do. */
export interface DraftCards {
  /** The cards of each workflow's newest draft; any other is superseded. */
  currentDraftIds: ReadonlySet<string>;
  tests: Map<string, DraftTest>;
  /** Draft id -> the task it was saved into. */
  saved: Map<string, { triggerId: string; name: string }>;
  /** Steps finished of the test running now, if any. */
  testProgress: { done: number; total: number } | null;
  onReview?: (entry: WorkflowDraftEntry) => void;
  onTestAgain?: (entry: WorkflowDraftEntry) => void;
  onContinue?: () => void;
  onOpenTask?: (triggerId: string) => void;
}

export const DraftCardsContext = createContext<DraftCards>({
  currentDraftIds: new Set(),
  tests: new Map(),
  saved: new Map(),
  testProgress: null,
});

export type Status =
  | { kind: "saved"; name: string; triggerId: string }
  | { kind: "testing"; done: number; total: number }
  | { kind: "passed"; result: WorkflowTestResult }
  | { kind: "approval"; result: WorkflowTestResult }
  | { kind: "irreversible"; result: WorkflowTestResult }
  | { kind: "failed"; result: WorkflowTestResult }
  | { kind: "untested" };

export function draftStatus(entry: WorkflowDraftEntry, cards: DraftCards): Status {
  const saved = entry.draftId ? cards.saved.get(entry.draftId) : undefined;
  if (saved) return { kind: "saved", ...saved };
  const test = entry.draftId ? cards.tests.get(entry.draftId) : undefined;
  if (test?.running) {
    const total = cards.testProgress?.total ?? placeSteps(entry.workflow.steps).length;
    return { kind: "testing", done: cards.testProgress?.done ?? 0, total };
  }
  const result = test?.result;
  if (!result) return { kind: "untested" };
  if (result.status === "passed") return { kind: "passed", result };
  if (result.status === "stopped_at_approval") return { kind: "approval", result };
  if (result.status === "stopped_before_irreversible") return { kind: "irreversible", result };
  return { kind: "failed", result };
}
