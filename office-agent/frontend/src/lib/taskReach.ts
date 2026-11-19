import { createContext, useCallback, useContext, useEffect, useState } from "react";

/** What a scheduled task can reach (decision 0048): its workspace's folders, Settings' Allowed
 * folders and the folders allowed for this task only. */
export interface TaskReach {
  workspace: { id: string; name: string; folders: string[] };
  allowed: { path: string; permission: "read" | "write" | "delete" }[];
  task: string[];
}

/** Where a folder an input names falls in a task's reach; null is outside it. */
export interface ReachCheck {
  path: string;
  inside: "workspace" | "task" | "allowed" | null;
  root: string | null;
  writable: boolean;
  exists: boolean;
}

type Failure = { error: string };

async function call<T>(url: string, init?: RequestInit): Promise<T | Failure> {
  const res = await fetch(url, init ? { ...init, headers: { "Content-Type": "application/json" } } : undefined).catch(() => null);
  if (!res) return { error: "Couldn't reach coscribe. Check that it's still running." };
  const body = (await res.json().catch(() => null)) as (T & Partial<Failure>) | null;
  if (!res.ok || body === null) return { error: body?.error ?? `Request failed (${res.status})` };
  return body;
}

const taskUrl = (taskId: string) => `/api/scheduled-tasks/${encodeURIComponent(taskId)}`;

const getTaskReach = (taskId: string) => call<TaskReach>(`${taskUrl(taskId)}/reach`);

export const checkReach = (taskId: string, path: string) =>
  call<ReachCheck>("/api/reach/check", { method: "POST", body: JSON.stringify({ task: taskId, path }) });

/** Only this task: its runs may read and write the folder. */
export const allowForTask = (taskId: string, path: string) =>
  call<{ task: string[] }>(`${taskUrl(taskId)}/folders`, { method: "POST", body: JSON.stringify({ path }) });

export const removeFromTask = (taskId: string, path: string) =>
  call<{ task: string[] }>(`${taskUrl(taskId)}/folders?path=${encodeURIComponent(path)}`, { method: "DELETE" });

/** The saved task a page shows, so a folder input on it is checked against its reach. */
export const TaskReachContext = createContext<{ taskId: string; onChanged: () => void } | null>(null);

export function useThisTaskReach() {
  return useContext(TaskReachContext);
}

/** A task's reach, read again when `changed` does or after `reload`. */
export function useTaskReach(taskId: string, changed = ""): { reach: TaskReach | null; reload: () => void } {
  const [reach, setReach] = useState<TaskReach | null>(null);
  const [version, setVersion] = useState(0);
  useEffect(() => {
    let live = true;
    void getTaskReach(taskId).then((result) => live && !("error" in result) && setReach(result));
    return () => {
      live = false;
    };
  }, [taskId, version, changed]);
  return { reach, reload: useCallback(() => setVersion((v) => v + 1), []) };
}
