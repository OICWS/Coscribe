import { useEffect, useRef, useState } from "react";
import { useAppearance } from "../lib/appearance";
import { formatElapsed, formatTokenCount } from "../lib/format";
import type { CompactionState } from "../state/reducer";

interface RunStatusProps {
  threadId: string;
  turnInFlight: boolean;
  compaction: CompactionState;
  /** When the server says the running turn started, for a page that opened mid-turn. */
  serverStartedAt: number | null;
  totalTokens: number;
  workflowTest?: { done: number; total: number } | null;
  /** Stop was pressed and the turn has not ended yet: a call in flight can take a moment. */
  stopping?: boolean;
}

// Outside the component: switching to another conversation and back mounts it afresh while the
// turn it times goes on.
const starts = new Map<string, { at: number; tokens: number }>();

/** Live "2m 5s · 1.2k tokens" line shown in the composer while a turn is
 * running -- elapsed time since this turn started, and how much
 * state.totalTokens (the same running total ContextRing shows) has grown
 * by since then. Both numbers tick/update live: the backend now sends a
 * "usage" WS event after every model response within a turn (see
 * conversation/session.py's _capture_segment_usage), not only once the whole turn
 * finishes, so a long multi-tool-call turn updates the token count as it
 * goes instead of jumping once at the end.
 *
 * Deliberately just the two numbers for now, not the expandable
 * "Editing Fundamentals.md ▾" running action list Claude Code's own
 * status line also shows -- that needs a live list of in-progress
 * actions coscribe doesn't track yet, a separate, larger piece of work. */
export function RunStatus({ threadId, turnInFlight, compaction, serverStartedAt, totalTokens, workflowTest = null, stopping = false }: RunStatusProps) {
  const [start, setStart] = useState<{ at: number; tokens: number } | null>(null);
  const [now, setNow] = useState(() => Date.now());
  const wasRunning = useRef(false);
  // The simple view's status line under the turn already shows the time; tokens mean little there.
  const simple = useAppearance().conversationView === "simple";

  useEffect(() => {
    if (!turnInFlight) {
      // Only a turn seen ending here: a page just mounted is not running until its state comes.
      if (wasRunning.current) starts.delete(threadId);
      wasRunning.current = false;
      setStart(null);
      return;
    }
    wasRunning.current = true;
    let entry = starts.get(threadId);
    // Seconds apart at most for the same turn (the send, then the server taking it); anything
    // further is a turn this page did not see end.
    if (serverStartedAt !== null && (!entry || Math.abs(entry.at - serverStartedAt) > 10_000)) {
      entry = { at: serverStartedAt, tokens: totalTokens };
    }
    entry ??= { at: Date.now(), tokens: totalTokens };
    starts.set(threadId, entry);
    setStart(entry);
    setNow(Date.now());
    const interval = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(interval);
    // Not keyed on totalTokens: it ticks during the turn being timed.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [threadId, turnInFlight, serverStartedAt]);

  useEffect(() => {
    if (compaction?.status !== "running") return;
    setNow(Date.now());
    const interval = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(interval);
  }, [compaction]);

  if (compaction?.status === "running") {
    return (
      <span className="min-w-0 truncate text-xs tabular-nums text-[var(--muted)]" data-testid="compact-status">
        {`Compacting conversation… ${formatElapsed(now - compaction.startedAt)}`}
      </span>
    );
  }

  if (!turnInFlight || start === null) return null;
  if (simple && !stopping && !workflowTest) return null;
  const tokenDelta = Math.max(0, totalTokens - start.tokens);

  return (
    // The time and tokens wait for a wide composer; "Stopping…" shows at any width, as the only
    // sign that the stop was received while the turn takes time to end.
    <span className={`${stopping ? "inline" : "hidden @[600px]:inline"} shrink-0 text-xs tabular-nums text-[var(--muted)]`} data-testid="run-status">
      {workflowTest && (
        <span data-testid="workflow-test-progress">
          Testing workflow {workflowTest.done}/{workflowTest.total}
          {(!simple || stopping) && " · "}
        </span>
      )}
      {stopping ? (
        "Stopping…"
      ) : simple ? null : (
        <>
          {formatElapsed(now - start.at)}
          {tokenDelta > 0 && <> · {formatTokenCount(tokenDelta)} tokens</>}
        </>
      )}
    </span>
  );
}
