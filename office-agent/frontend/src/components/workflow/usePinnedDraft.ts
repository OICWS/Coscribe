import { useEffect, useState, type RefObject } from "react";
import { latestWorkflowDraft, type WorkflowDraftEntry } from "../../lib/transcriptGrouping";
import type { LogItem } from "../../state/reducer";

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
    // The newest few are enough: a closed bar only matters while its draft is the latest.
    localStorage.setItem(CLOSED_KEY, JSON.stringify([...ids].slice(-50)));
  } catch {
    // Without storage a closed bar comes back after a reload, which only costs a click.
  }
}

// Each revision gets its own draft id, so closing one version's bar doesn't hide the next one's.
function closeKeyOf(draft: WorkflowDraftEntry): string {
  return draft.draftId ?? draft.id;
}

/** The newest unsaved draft to keep at the bottom of the chat while its card is scrolled away:
 * only once the turn that made it has ended (a draft the model is still testing or revising
 * isn't the one to review yet), and not after the person closed the bar for that draft. */
export function draftToPin(
  latest: WorkflowDraftEntry | null,
  saved: ReadonlyMap<string, unknown>,
  view: { cardVisible: boolean; turnInFlight: boolean; closed: ReadonlySet<string> },
): WorkflowDraftEntry | null {
  if (latest === null || (latest.draftId && saved.has(latest.draftId))) return null;
  if (view.cardVisible || view.turnInFlight || view.closed.has(closeKeyOf(latest))) return null;
  return latest;
}

export function usePinnedDraft(
  items: LogItem[],
  saved: ReadonlyMap<string, unknown>,
  turnInFlight: boolean,
  scrollRef: RefObject<HTMLDivElement | null>,
) {
  const latest = latestWorkflowDraft(items);
  const [closed, setClosed] = useState(readClosed);
  const [cardVisible, setCardVisible] = useState(true);
  const unsaved = latest !== null && !(latest.draftId && saved.has(latest.draftId));
  const cardId = unsaved ? latest.id : null;

  useEffect(() => {
    const root = scrollRef.current;
    const card = cardId ? root?.querySelector(`[data-draft-card="${cardId}"]`) : null;
    if (!root || !card) {
      setCardVisible(true);
      return;
    }
    const observer = new IntersectionObserver(([entry]) => setCardVisible(entry.isIntersecting), {
      root,
      threshold: 0.2,
    });
    observer.observe(card);
    return () => observer.disconnect();
  }, [cardId, items.length, scrollRef]);

  return {
    pinned: draftToPin(latest, saved, { cardVisible, turnInFlight, closed }),
    show: () => {
      const card = cardId ? scrollRef.current?.querySelector(`[data-draft-card="${cardId}"]`) : null;
      card?.scrollIntoView({ behavior: "smooth", block: "center" });
    },
    close: () => {
      if (!latest) return;
      const next = new Set(closed).add(closeKeyOf(latest));
      setClosed(next);
      writeClosed(next);
    },
  };
}
