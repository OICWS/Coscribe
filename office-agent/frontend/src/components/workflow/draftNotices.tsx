import { useState } from "react";
import { currentWorkflowDrafts, draftsInTheWorks, workflowTests, type WorkflowDraftEntry } from "../../lib/transcriptGrouping";
import type { LogItem } from "../../state/reducer";
import type { ScheduledTask } from "../../types/settings";
import { WorkflowIcon } from "../icons";
import type { Notice } from "../NoticeStack";
import { type DraftCards, draftStatus, type Status } from "./draftCards";

const CLOSED_KEY = "coscribe.closedDraftBars";

function readClosed(): Set<string> {
  try {
    const raw = localStorage.getItem(CLOSED_KEY);
    return new Set(raw ? (JSON.parse(raw) as string[]) : []);
  } catch {
    return new Set();
  }
}

function writeClosed(ids: Set<string>) {
  try {
    localStorage.setItem(CLOSED_KEY, JSON.stringify([...ids].slice(-50)));
  } catch {
    // Without storage a closed notice comes back after a reload, which only costs a click.
  }
}

// Each revision gets its own draft id, so closing one version's notice doesn't hide the next one's.
function closeKeyOf(draft: WorkflowDraftEntry): string {
  return draft.draftId ?? draft.id;
}

/** The drafts to offer above the message box: each workflow's newest, while it is unsaved and
 * the person hasn't closed its notice. */
export function draftsToOffer(
  items: LogItem[],
  saved: ReadonlyMap<string, unknown>,
  closed: ReadonlySet<string>,
): WorkflowDraftEntry[] {
  return currentWorkflowDrafts(items).filter(
    (draft) => draft.draftId !== null && !saved.has(draft.draftId) && !closed.has(closeKeyOf(draft)),
  );
}

function stateWords(status: Status): string {
  switch (status.kind) {
    case "testing":
      return `Testing ${status.done}/${status.total}`;
    case "passed":
      return "Tested";
    case "approval":
    case "irreversible":
      return "Partly tested";
    case "failed":
      return "Test failed";
    default:
      return "Not tested";
  }
}

/** What a conversation's draft cards share that comes from outside it: which drafts the tasks
 * were saved from, the test running now, and the buttons' actions. */
export function draftCardsFrom(
  tasks: ScheduledTask[],
  testProgress: DraftCards["testProgress"],
  on: { testAgain?: (draft: WorkflowDraftEntry) => void; openTask: (task: ScheduledTask) => void },
): Pick<DraftCards, "saved" | "testProgress" | "onTestAgain" | "onContinue" | "onOpenTask"> {
  const saved = new Map<string, { triggerId: string; name: string }>();
  for (const task of tasks) for (const id of task.drafts ?? []) saved.set(id, { triggerId: task.trigger_id, name: task.name });
  return {
    saved,
    testProgress,
    onTestAgain: on.testAgain,
    onContinue: () => document.querySelector<HTMLTextAreaElement>('[data-testid="composer"] textarea')?.focus(),
    onOpenTask: (triggerId) => {
      const task = tasks.find((t) => t.trigger_id === triggerId);
      if (task) on.openTask(task);
    },
  };
}

export function useDraftNotices(
  items: LogItem[],
  turnInFlight: boolean,
  cards: Pick<DraftCards, "saved" | "testProgress">,
  on: { save: (draft: WorkflowDraftEntry) => Promise<string | null>; review: (draft: WorkflowDraftEntry) => void },
): Notice[] {
  const [closed, setClosed] = useState(readClosed);
  // Why a save from a notice failed, shown on that notice.
  const [failed, setFailed] = useState<Record<string, string>>({});
  const working = draftsInTheWorks(items, turnInFlight);
  const tests = workflowTests(items, turnInFlight);
  const status = { ...cards, currentDraftIds: new Set<string>(), inTheWorks: working, tests };
  // A draft the running reply may still fix shows up once the reply is done.
  const offered = draftsToOffer(items, cards.saved, closed).filter((draft) => !working.has(draft.id));
  return offered.map((draft) => {
    const state = draftStatus(draft, status);
    return {
      id: `draft:${draft.id}`,
      icon: <WorkflowIcon className="h-4 w-4" />,
      title: draft.triggerId ? `Changes to “${draft.name}”` : draft.name,
      detail: (failed[draft.id] || draft.triggerId ? "changes to a saved task" : "workflow draft"),
      state: failed[draft.id] ? "Not saved" : stateWords(state),
      ready: state.kind === "passed",
      onOpen: () =>
        document
          .querySelector(`[data-draft-card="${draft.id}"]`)
          ?.scrollIntoView({ behavior: "smooth", block: "center" }),
      actions: [
        { label: "Review", onClick: () => on.review(draft), title: "Look over each step before saving" },
        {
          label: draft.triggerId ? "Save changes" : "Save…",
          disabled: state.kind === "testing",
          onClick: () =>
            void on.save(draft).then((error) => setFailed((was) => ({ ...was, [draft.id]: error ?? "" }))),
        },
      ],
      onDismiss: () => {
        const next = new Set(closed).add(closeKeyOf(draft));
        setClosed(next);
        writeClosed(next);
      },
      dismissTitle: "Hide this; the draft stays in the conversation",
    };
  });
}
