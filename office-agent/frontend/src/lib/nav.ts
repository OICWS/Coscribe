import { useEffect } from "react";

// Must match tools/bookkeeping/scheduled_tasks.py's SCHEDULED_THREAD_PREFIX: every
// scheduled run's conversation id starts with it.
export const SCHEDULED_THREAD_PREFIX = "scheduled-";

/** Fired on window after an in-page navigation; App.tsx listens for it
 * (and popstate) and shows the page the URL now names. */
export const THREAD_CHANGE_EVENT = "coscribe:threadchange";

export type View = "chat" | "scheduled" | "artifacts" | "sessions";

/** Which page the URL names: a conversation (the default), the
 * Scheduled portal / one task's page, the Artifacts page or the page of
 * every session. `thread`
 * stays in the URL on those pages so returning to chat reopens the same
 * conversation. */
export function readPage(): { view: View; task: string | null } {
  const params = new URL(window.location.href).searchParams;
  const named = params.get("view");
  const view: View = named === "scheduled" || named === "artifacts" || named === "sessions" ? named : "chat";
  return { view, task: view === "scheduled" ? params.get("task") : null };
}

/** The URL is the single source of truth for which page is open, so
 * reload, Back/Forward and a pasted link all keep working. Always fires
 * the event, even when the URL didn't change, so e.g. Run now from the
 * portal still lands on the run's conversation. */
function navigate(change: (params: URLSearchParams) => void, { replace = false } = {}): void {
  const url = new URL(window.location.href);
  change(url.searchParams);
  if (url.toString() !== window.location.href) {
    if (replace) window.history.replaceState(null, "", url.toString());
    else window.history.pushState(null, "", url.toString());
  }
  window.dispatchEvent(new Event(THREAD_CHANGE_EVENT));
}

export function goToThread(threadId: string): void {
  navigate((params) => {
    params.set("thread", threadId);
    params.delete("view");
    params.delete("task");
  });
}

/** Back to the current conversation from a Scheduled page. */
export function showChat(): void {
  navigate((params) => {
    params.delete("view");
    params.delete("task");
  });
}

/** The Scheduled portal (taskId null) or one task's page. */
export function showScheduled(taskId: string | null, options?: { replace?: boolean }): void {
  navigate((params) => {
    params.set("view", "scheduled");
    if (taskId) params.set("task", taskId);
    else params.delete("task");
  }, options);
}

/** The Artifacts page. */
export function showArtifacts(): void {
  navigate((params) => {
    params.set("view", "artifacts");
    params.delete("task");
  });
}

/** Every session, active or archived, as one list. */
export function showSessions(): void {
  navigate((params) => {
    params.set("view", "sessions");
    params.delete("task");
  });
}

// A thread started here has no history on the server, so the page can show the new-conversation
// layout before the socket's empty history arrives; otherwise the composer mounts in the chat
// layout, takes a prefilled draft, and is remounted (losing it) when the layout switches.
const freshThreads = new Set<string>();

export function startNewThread(): string {
  const id = crypto.randomUUID().slice(0, 8);
  freshThreads.add(id);
  goToThread(id);
  return id;
}

/** True while a thread this tab just started waits for its empty history. Once that arrives the
 * server is the source of truth again, so a later return to the thread waits for it like any other. */
export function useFreshThread(threadId: string, historyReceived: boolean): boolean {
  useEffect(() => {
    if (historyReceived) freshThreads.delete(threadId);
  }, [historyReceived, threadId]);
  return freshThreads.has(threadId);
}
