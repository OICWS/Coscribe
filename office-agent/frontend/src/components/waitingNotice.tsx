import { useEffect, useState } from "react";
import { summarizeItem } from "../lib/transcriptGrouping";
import type { LogItem } from "../state/reducer";
import { HandIcon, MessageCircleIcon } from "./icons";
import type { Notice } from "./NoticeStack";

type Waiting = Extract<LogItem, { kind: "approval" } | { kind: "plan" }>;

/** The newest call or plan the reply waits on the person for. A question is left out: its panel
 * already sits above the message box. */
function waitingItem(items: LogItem[]): Waiting | null {
  return (
    items.findLast(
      (item): item is Waiting => (item.kind === "approval" || item.kind === "plan") && item.status === "pending",
    ) ?? null
  );
}

const cardOf = (id: string) => document.querySelector<HTMLElement>(`[data-waiting="${CSS.escape(id)}"]`);

/** Whether the card an item renders as is out of sight, scrolled away in the conversation. A card
 * not on the page yet counts as in sight, so the notice doesn't flash while it mounts. */
function useOutOfSight(id: string | null, itemCount: number): boolean {
  const [hiddenId, setHiddenId] = useState<string | null>(null);
  useEffect(() => {
    if (!id) return;
    const card = cardOf(id);
    if (!card) return;
    const observer = new IntersectionObserver(([entry]) => setHiddenId(entry.isIntersecting ? null : id));
    observer.observe(card);
    return () => observer.disconnect();
  }, [id, itemCount]);
  return id !== null && hiddenId === id;
}

/** A notice for what the reply waits on, while its card is scrolled out of sight. */
export function useWaitingNotice(items: LogItem[]): Notice | null {
  const item = waitingItem(items);
  const hidden = useOutOfSight(item?.id ?? null, items.length);
  if (!item || !hidden) return null;
  const show = () => cardOf(item.id)?.scrollIntoView({ behavior: "smooth", block: "center" });
  const approval = item.kind === "approval";
  return {
    id: `waiting:${item.id}`,
    icon: approval ? <HandIcon className="h-4 w-4" /> : <MessageCircleIcon className="h-4 w-4" />,
    title: approval ? "Waiting for your approval" : "A plan waits for your answer",
    plainTitle: true,
    detail: approval ? summarizeItem(item).replace(/^Approve:\s*/, "") : undefined,
    onOpen: show,
    openTitle: "Show it in the conversation",
    actions: [{ label: "Show", onClick: show }],
  };
}
