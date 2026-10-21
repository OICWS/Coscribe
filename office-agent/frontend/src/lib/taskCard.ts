/** The task list the model keeps (task_create / task_update / task_list), and
 * the live card that replaces the stretch of a turn it was worked in. Render
 * time only: the narration and the calls stay in the history. */

import type { LogItem } from "../state/reducer";
import type { ToolRunGroup, TranscriptEntry } from "./transcriptGrouping";
import type { ProgressItem, ProgressStatus } from "./workflowProgress";

type ToolOrApprovalItem = Extract<LogItem, { kind: "tool" | "approval" }>;
type PlanItem = Extract<LogItem, { kind: "plan" }>;

export interface TaskCardEntry {
  kind: "task_card";
  id: string;
  tasks: ProgressItem[];
  /** The calls made while an item was in progress, by item id; "" holds the
   * ones made while none was. */
  calls: Record<string, ToolOrApprovalItem[]>;
  /** Items (or "" for the card) with a failed call, shown even when the model
   * has not updated the list yet. */
  failed: string[];
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

const isTaskTool = (name: string) => name === "task_create" || name === "task_update" || name === "task_list";

/** One task call applied to the list. A call still running counts from its
 * arguments, so the card moves as soon as the model acts. */
function applyTaskCall(tasks: ProgressItem[], item: ToolOrApprovalItem): ProgressItem[] {
  if (item.toolName === "task_create") {
    const created = taskOf(item.result) ?? (typeof item.arguments.content === "string"
      ? { id: `pending-${item.id}`, content: item.arguments.content, status: "pending" as const }
      : null);
    return created ? [...tasks.filter((task) => task.id !== created.id), created] : tasks;
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
  }
  return tasks;
}

/** What the Plan panel shows: the list, and the plan text last proposed. */
export function planPanelData(items: LogItem[]): { tasks: ProgressItem[]; plan: string | null } {
  const plans = items.filter((item): item is PlanItem => item.kind === "plan");
  return { tasks: taskListOf(items), plan: plans.length > 0 ? plans[plans.length - 1].plan : null };
}

const allDone = (tasks: ProgressItem[]) => tasks.length > 0 && tasks.every((task) => task.status === "completed");

/** What stays drawn in the transcript when a stretch is replaced: anything
 * the person has to answer, and what is not narration or a call. */
function staysVisible(entry: TranscriptEntry): boolean {
  return entry.kind !== "agent" && entry.kind !== "tool_run";
}

/** Replaces the stretch of a turn from its first task call to its last call
 * with one card: the narration and the calls of that stretch are not drawn,
 * the calls open under the item that was in progress. An approval waiting on
 * the person and the person's own questions stay in the transcript. A reply
 * after the last call stays too, once the turn is over or the list is done. */
export function foldTaskCard(entries: TranscriptEntry[], live: boolean, tasksBefore: ProgressItem[] = []): TurnEntry[] {
  const first = entries.findIndex((entry) => entry.kind === "tool_run" && entry.items.some((i) => i.kind === "tool" && isTaskTool(i.toolName)));
  if (first < 0) return entries;

  const startGroup = entries[first] as ToolRunGroup;
  const split = startGroup.items.findIndex((item) => item.kind === "tool" && isTaskTool(item.toolName));
  const out: TurnEntry[] = entries.slice(0, first);
  if (split > 0) out.push({ ...startGroup, items: startGroup.items.slice(0, split) });

  let lastCall = first;
  for (let i = first; i < entries.length; i++) if (entries[i].kind === "tool_run") lastCall = i;

  let tasks = tasksBefore;
  const calls: Record<string, ToolOrApprovalItem[]> = {};
  const failed = new Set<string>();
  const kept: TurnEntry[] = [];
  let active = "";

  for (let i = first; i <= lastCall; i++) {
    const entry = entries[i];
    if (entry.kind !== "tool_run") {
      if (staysVisible(entry)) kept.push(entry);
      continue;
    }
    const waiting: ToolOrApprovalItem[] = [];
    for (const item of i === first ? entry.items.slice(split) : entry.items) {
      if (item.kind === "approval" && item.status === "pending") {
        waiting.push(item);
        continue;
      }
      if (item.kind === "tool" && isTaskTool(item.toolName)) {
        tasks = applyTaskCall(tasks, item);
        active = tasks.find((task) => task.status === "in_progress")?.id ?? "";
        continue;
      }
      (calls[active] ??= []).push(item);
      if (item.isError) failed.add(active);
    }
    if (waiting.length > 0) kept.push({ kind: "tool_run", id: `run-${waiting[0].id}`, items: waiting });
  }

  const card: TaskCardEntry = { kind: "task_card", id: `taskcard-${startGroup.items[split].id}`, tasks, calls, failed: [...failed] };
  out.push(card, ...kept);
  const trailing = entries.slice(lastCall + 1);
  return out.concat(live && !allDone(tasks) ? trailing.filter(staysVisible) : trailing);
}
