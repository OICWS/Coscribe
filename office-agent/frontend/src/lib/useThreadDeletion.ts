import { useCallback, useState } from "react";
import type { ThreadSummary } from "../types/session";
import { startNewThread } from "./nav";
import { deleteThread } from "./rest";

export type DeleteState = "deleting" | "failed";
/** A sidebar row: the conversation, and whether it is being deleted or its delete failed. */
export type ListedThread = ThreadSummary & { deleteState?: DeleteState };

const without = (states: Record<string, DeleteState>, id: string) => {
  const { [id]: _, ...rest } = states;
  return rest;
};

/** Deleting conversations from the sidebar. The server first stops a running turn (waiting up to
 * 15 s for it) and keeps what the conversation made, so a row shows it is being deleted until the
 * server is done, then leaves, or stays marked when the delete failed. */
export function useThreadDeletion(threads: ThreadSummary[], onDone: () => void) {
  const [states, setStates] = useState<Record<string, DeleteState>>({});
  // Deleted on the server, still in a list read before that.
  const [gone, setGone] = useState<ReadonlySet<string>>(new Set());

  const remove = useCallback(
    (ids: string[], currentId: string) => {
      if (ids.includes(currentId)) startNewThread(); // leave it before it is gone
      setStates((current) => ({ ...current, ...Object.fromEntries(ids.map((id) => [id, "deleting" as const])) }));
      const each = ids.map((id) =>
        deleteThread(id).then(
          () => {
            setGone((current) => new Set([...current, id]));
            setStates((current) => without(current, id));
          },
          () => setStates((current) => ({ ...current, [id]: "failed" })),
        ),
      );
      void Promise.all(each).then(onDone);
    },
    [onDone],
  );

  const listed: ListedThread[] = threads
    .filter((t) => !gone.has(t.thread_id))
    .map((t) => (states[t.thread_id] ? { ...t, deleteState: states[t.thread_id] } : t));
  return { listed, remove };
}
