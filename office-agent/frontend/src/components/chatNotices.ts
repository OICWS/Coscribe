import type { ReactNode } from "react";
import type { WorkflowDraftEntry } from "../lib/transcriptGrouping";
import type { LogItem } from "../state/reducer";
import type { Notice } from "./NoticeStack";
import { useOutputNotices } from "./outputNotices";
import { saveOfferNotice } from "./saveOffer";
import { useWaitingNotice } from "./waitingNotice";
import type { DraftCards } from "./workflow/draftCards";
import { useDraftNotices } from "./workflow/draftNotices";

interface ChatNoticeActions {
  saveDraft: (draft: WorkflowDraftEntry) => Promise<string | null>;
  reviewDraft: (draft: WorkflowDraftEntry) => void;
  /** The save offer's two ways to keep a job, each given its name. */
  saveAsWorkflow: (name: string) => void;
  saveAsSkill: (name: string) => void;
  dismissOffer: () => void;
  /** Shows a file in its panel; false when the app can't show it. */
  viewFile: (path: string) => boolean;
}

/** What waits on the person above a conversation's message box, oldest first: what the
 * conversation made, its unsaved drafts, the offer to save the job a finished reply did, and the
 * card the reply waits on when it is scrolled away. With the picture viewer the notices open. */
export function useChatNotices(
  conversation: { threadId: string; refreshKey: string; items: LogItem[]; turnInFlight: boolean },
  cards: Pick<DraftCards, "saved" | "testProgress">,
  saveOffer: { steps: number; name: string } | null,
  on: ChatNoticeActions,
): { notices: Notice[]; overlay: ReactNode } {
  const { threadId, refreshKey, items, turnInFlight } = conversation;
  const made = useOutputNotices(threadId, refreshKey, { view: on.viewFile });
  const drafts = useDraftNotices(items, turnInFlight, cards, { save: on.saveDraft, review: on.reviewDraft });
  const waiting = useWaitingNotice(items);
  const offer =
    saveOffer && !turnInFlight
      ? saveOfferNotice(saveOffer, { workflow: on.saveAsWorkflow, skill: on.saveAsSkill, dismiss: on.dismissOffer })
      : null;
  const notices = [...made.notices, ...drafts, ...(offer ? [offer] : []), ...(waiting ? [waiting] : [])];
  return { notices, overlay: made.overlay };
}
