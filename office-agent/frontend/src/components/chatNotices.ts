import type { WorkflowDraftEntry } from "../lib/transcriptGrouping";
import type { LogItem } from "../state/reducer";
import type { Notice } from "./NoticeStack";
import { saveOfferNotice } from "./saveOffer";
import type { DraftCards } from "./workflow/draftCards";
import { useDraftNotices } from "./workflow/draftNotices";

interface ChatNoticeActions {
  saveDraft: (draft: WorkflowDraftEntry) => Promise<string | null>;
  reviewDraft: (draft: WorkflowDraftEntry) => void;
  /** The save offer's two ways to keep a job, each given its name. */
  saveAsWorkflow: (name: string) => void;
  saveAsSkill: (name: string) => void;
  dismissOffer: () => void;
}

/** What waits on the person above a conversation's message box: its unsaved drafts, and the
 * offer to save the job a finished reply did. */
export function useChatNotices(
  items: LogItem[],
  turnInFlight: boolean,
  cards: Pick<DraftCards, "saved" | "testProgress">,
  saveOffer: { steps: number; name: string } | null,
  on: ChatNoticeActions,
): Notice[] {
  const drafts = useDraftNotices(items, turnInFlight, cards, { save: on.saveDraft, review: on.reviewDraft });
  if (!saveOffer || turnInFlight) return drafts;
  const offer = saveOfferNotice(saveOffer, {
    workflow: on.saveAsWorkflow,
    skill: on.saveAsSkill,
    dismiss: on.dismissOffer,
  });
  return [...drafts, offer];
}
