import { useEffect, useRef } from "react";
import type { LogItem } from "../state/reducer";
import { requestAttention, setSessionBusy } from "./electron";

const WAITING_ON_PERSON = (item: LogItem): boolean =>
  (item.kind === "approval" || item.kind === "question" || item.kind === "plan") && item.status === "pending";

/** Tells the desktop shell when a turn runs (it keeps the computer awake) and when coscribe
 * needs the person: a turn ended, or an approval, question or plan is waiting. */
export function useSessionSignals(threadId: string, turnInFlight: boolean, items: LogItem[]): void {
  const waiting = items.some(WAITING_ON_PERSON);
  const previous = useRef({ threadId, turnInFlight, waiting });

  useEffect(() => {
    setSessionBusy(turnInFlight);
  }, [turnInFlight]);
  useEffect(() => () => setSessionBusy(false), []);

  useEffect(() => {
    const before = previous.current;
    previous.current = { threadId, turnInFlight, waiting };
    // Switching conversations resets what is shown; that is not a turn ending.
    if (before.threadId !== threadId) return;
    if ((before.turnInFlight && !turnInFlight) || (!before.waiting && waiting)) requestAttention();
  }, [threadId, turnInFlight, waiting]);
}
