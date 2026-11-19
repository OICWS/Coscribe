/** The task list the model keeps (task_create / task_update / task_list), and
 * where the conversation shows it: one card, under the latest call that changed
 * the list, so it moves to the bottom each time the list changes. Once every
 * item is done it folds into one line. Render time only: the calls stay in the
 * history.
 *
 * A background agent or script started while an item is in progress is bound to
 * that item, so the card can show what the task is doing. The model says nothing
 * of the link: it is inferred from when the task started. */

import type { LogItem } from "../state/reducer";
import type { TranscriptEntry } from "./transcriptGrouping";
import type { ProgressItem, ProgressStatus } from "./workflowProgress";

type ToolOrApprovalItem = Extract<LogItem, { kind: "tool" | "approval" }>;
type PlanItem = Extract<LogItem, { kind: "plan" }>;

export interface TaskCardEntry {
  kind: "task_card";
  id: string;
  tasks: ProgressItem[];
  /** Every item is done: shown as one line that opens to the list. */
  done: boolean;
  /** The background tasks each item started, by item id. */
  bound: Record<string, string[]>;
}

export type TurnEntry = TranscriptEntry | TaskCardEntry;

const STATUSES: readonly string[] = ["pending", "in_progress", "completed"];

function recordOf(value: unknown): Record<string, unknown> | null {
  let parsed = value;
  if (typeof parsed === "string") {
    try {
      parsed = JSON.parse(parsed);
    } catch {
      return null;
    }
  }
  return typeof parsed === "object" && parsed !== null && !Array.isArray(parsed) ? (parsed as Record<string, unknown>) : null;
}

function taskOf(value: unknown): ProgressItem | null {
  const record = recordOf(value);
  if (!record || record.id === undefined || typeof record.content !== "string") return null;
  const status = STATUSES.includes(String(record.status)) ? (record.status as ProgressStatus) : "pending";
  return { id: String(record.id), content: record.content, status };
}

const BACKGROUND_STARTERS: readonly string[] = ["spawn_agent_background", "run_background_script", "run_background_command"];

/** The background task a call started: one of the starters, or a script that moved to the
 * background (at its time limit, or because the person wrote mid-turn). Not known until the
 * call's result is in; an approved call carries its result on the approval item. */
function startedTaskId(item: ToolOrApprovalItem): string | null {
  const record = recordOf(item.result);
  const started = BACKGROUND_STARTERS.includes(item.toolName) || record?.status === "running_in_background";
  const taskId = record?.task_id;
  return started && typeof taskId === "string" && taskId !== "" ? taskId : null;
}

const allDone = (tasks: ProgressItem[]) => tasks.length > 0 && tasks.every((task) => task.status === "completed");

const isTaskTool = (name: string) => name === "task_create" || name === "task_update" || name === "task_list";

/** One task call applied to the list. A call still running counts from its
 * arguments, so the card moves as soon as the model acts. */
function applyTaskCall(tasks: ProgressItem[], item: ToolOrApprovalItem): ProgressItem[] {
  if (item.toolName === "task_create") {
    const created = taskOf(item.result) ?? (typeof item.arguments.content === "string"
      ? { id: `pending-${item.id}`, content: item.arguments.content, status: "pending" as const }
      : null);
    if (!created) return tasks;
    // As task_create does on the server: a list whose every item is done is over, and a new
    // item starts the next one.
    const kept = allDone(tasks) ? [] : tasks.filter((task) => task.id !== created.id);
    return [...kept, created];
  }
  if (item.toolName === "task_update") {
    const updated = taskOf(item.result);
    const id = updated?.id ?? String(item.arguments.task_id ?? "");
    const status = updated?.status ?? (STATUSES.includes(String(item.arguments.status)) ? (item.arguments.status as ProgressStatus) : null);
    return status ? tasks.map((task) => (task.id === id ? { ...task, status } : task)) : tasks;
  }
  if (item.toolName === "task_list" && Array.isArray(item.result)) {
    const listed = item.result.map(taskOf).filter((task): task is ProgressItem => task !== null);
    return listed.length > 0 ? listed : tasks;
  }
  return tasks;
}

/** The task list as the conversation left it, from `tasks` it started with. */
export function taskListOf(items: LogItem[], tasks: ProgressItem[] = []): ProgressItem[] {
  for (const item of items) {
    if (item.kind === "tool" && isTaskTool(item.toolName)) tasks = applyTaskCall(tasks, item);
    else if (item.kind === "plan" && item.tasks) tasks = item.tasks;
  }
  return tasks;
}

/** What the Plan panel shows: the list, the plan text last proposed, and that plan's id while
 * it waits for an answer (its list can be edited then). */
export function planPanelData(items: LogItem[]): { tasks: ProgressItem[]; plan: string | null; pendingPlanId: string | null } {
  const last = items.findLast((item): item is PlanItem => item.kind === "plan");
  return { tasks: taskListOf(items), plan: last ? last.plan : null, pendingPlanId: last?.status === "pending" ? last.id : null };
}

/** Where the list is shown, by the id of the task call it is shown under. Only a
 * call that changed the list counts. The card goes under the last such call; a
 * finished list keeps its done line where it finished, and the next list gets a card of its own. */
export function taskCardPlaces(items: LogItem[]): Record<string, TaskCardEntry> {
  const changes: { id: string; tasks: ProgressItem[] }[] = [];
  let tasks: ProgressItem[] = [];
  const bound: Record<string, string[]> = {};
  // Several items can be in progress at once; a task started now belongs to the one that
  // started last, the likeliest to be what the model is doing.
  const startedOrder: string[] = [];
  let active = "";
  for (const item of items) {
    // An approved plan whose list the person edited replaces the list.
    if (item.kind === "plan" && item.tasks) {
      if (JSON.stringify(item.tasks) !== JSON.stringify(tasks)) changes.push({ id: item.id, tasks: item.tasks });
      tasks = item.tasks;
      continue;
    }
    if (item.kind !== "tool" && item.kind !== "approval") continue;
    if (item.kind === "approval" || !isTaskTool(item.toolName)) {
      const started = startedTaskId(item);
      if (started && active && !bound[active]?.includes(started)) (bound[active] ??= []).push(started);
      continue;
    }
    const before = new Set(tasks.filter((task) => task.status === "in_progress").map((task) => task.id));
    const next = applyTaskCall(tasks, item);
    if (JSON.stringify(next) !== JSON.stringify(tasks)) changes.push({ id: item.id, tasks: next });
    tasks = next;
    const running = tasks.filter((task) => task.status === "in_progress").map((task) => task.id);
    for (const taskId of running) if (!before.has(taskId)) startedOrder.push(taskId);
    active = [...startedOrder].reverse().find((taskId) => running.includes(taskId)) ?? "";
  }
  const places: Record<string, TaskCardEntry> = {};
  changes.forEach((change, i) => {
    const last = i === changes.length - 1;
    const done = allDone(change.tasks);
    if (last ? change.tasks.length > 0 : done && !allDone(changes[i + 1].tasks)) {
      const own = Object.fromEntries(change.tasks.filter((task) => bound[task.id]).map((task) => [task.id, bound[task.id]]));
      places[change.id] = { kind: "task_card", id: `taskcard-${change.id}`, tasks: change.tasks, done, bound: own };
    }
  });
  return places;
}

/** A turn's entries with the task calls taken out of their runs, and the list
 * put where `places` says. */
export function foldTaskCard(entries: TranscriptEntry[], places: Record<string, TaskCardEntry>): TurnEntry[] {
  const out: TurnEntry[] = [];
  for (const entry of entries) {
    if (entry.kind !== "tool_run") {
      out.push(entry);
      if (places[entry.id]) out.push(places[entry.id]);
      continue;
    }
    let run: ToolOrApprovalItem[] = [];
    const flush = () => {
      if (run.length > 0) out.push({ ...entry, id: `run-${run[0].id}`, items: run });
      run = [];
    };
    for (const item of entry.items) {
      if (item.kind !== "tool" || !isTaskTool(item.toolName)) run.push(item);
      else if (places[item.id]) {
        flush();
        out.push(places[item.id]);
      }
    }
    if (run.length === entry.items.length) out.push(entry);
    else flush();
  }
  return out;
}
