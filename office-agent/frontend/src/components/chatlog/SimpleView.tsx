import { useContext, useEffect, useState } from "react";
import { formatElapsed } from "../../lib/format";
import { currentActivity } from "../../lib/simpleView";
import { blockedWriteOf, type ToolRunGroup, type Turn } from "../../lib/transcriptGrouping";
import { BlockedFolderCard } from "../BlockedFolderCard";
import { ConnectorTools } from "./contexts";

// Kept outside the component: the line unmounts while a card waits for the person, and its time
// must go on from the turn's start when it comes back.
const starts = new Map<string, number>();

function startOf(turn: Turn): number {
  let start = starts.get(turn.id);
  if (start === undefined) {
    const sent = turn.userItem?.sentAt ? Date.parse(turn.userItem.sentAt) : NaN;
    start = Number.isNaN(sent) ? Date.now() : Math.min(sent, Date.now());
    starts.set(turn.id, start);
  }
  return start;
}

/** The simple view's one line under a running turn: what it is doing and for how long. */
export function SimpleStatus({ turn }: { turn: Turn }) {
  const connectorTools = useContext(ConnectorTools);
  const start = startOf(turn);
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const interval = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(interval);
  }, []);
  return (
    <div role="status" data-testid="simple-status" className="flex items-baseline gap-1.5 text-sm">
      <span className="shimmer-text">{currentActivity(turn.items, connectorTools)}</span>
      <span className="tabular-nums text-xs text-[var(--muted)]">{formatElapsed(now - start)}</span>
    </div>
  );
}

/** A tool run the simple view keeps for its card: a refused write's offer of folder access. */
export function BlockedWriteCards({ group }: { group: ToolRunGroup }) {
  return (
    <>
      {group.items.map((item) => {
        const blocked = blockedWriteOf(item);
        return blocked ? <BlockedFolderCard key={item.id} blocked={blocked} /> : null;
      })}
    </>
  );
}
