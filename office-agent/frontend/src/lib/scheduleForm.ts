import type { CreateScheduledTaskPayload, ScheduledTask, ScheduleKind } from "../types/settings";
import type { Workflow } from "../types/workflow";
import type { TaskDraft } from "../types/wire";

// The schedule part of the create/edit form (components/ScheduleFields.tsx): its starting values
// and what it saves.

export interface ScheduleForm {
  kind: ScheduleKind;
  time: string;
  weekday: number;
  /** Monthly's "starts on" date. */
  date: string;
  minutes: number;
  folder: string;
  pattern: string;
  /** The workflow's file input a new file goes to. */
  input: string;
  /** "connector" (decision 0039): the tool asked, its arguments, which input takes which field
   * of an item, the most runs an hour, and the person's OK for a tool not marked read-only.
   * "webhook" (decision 0040) uses the fields and the limit, for an event. */
  tool: string;
  args: Record<string, unknown>;
  inputsFrom: Record<string, string>;
  perHour: number;
  trustUnmarked: boolean;
}

/** Mirrors schedule_rule.py's DEFAULT_PER_HOUR and MAX_PER_HOUR. */
const DEFAULT_PER_HOUR = 30;
export const MAX_PER_HOUR = 120;

function todayIso(): string {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
}

function dateForDayOfMonth(day: number): string {
  const today = new Date();
  const candidate = new Date(today.getFullYear(), today.getMonth(), day);
  if (candidate < today) candidate.setMonth(candidate.getMonth() + 1);
  return `${candidate.getFullYear()}-${String(candidate.getMonth() + 1).padStart(2, "0")}-${String(candidate.getDate()).padStart(2, "0")}`;
}

/** Best-effort "starts on" date for a monthly task: ScheduleRule stores only a day of the month,
 * so this picks the nearest real date with it (or start_date) for display; saving re-derives
 * both from the date picked. */
function initialDate(task: ScheduledTask | null, draft: TaskDraft | undefined): string {
  if (draft?.start_date) return draft.start_date;
  if (draft?.kind === "monthly") return dateForDayOfMonth(draft.day_of_month ?? 1);
  if (task?.schedule.start_date) return task.schedule.start_date;
  if (task?.schedule.kind === "monthly") return dateForDayOfMonth(task.schedule.day_of_month ?? 1);
  return todayIso();
}

const KNOWN = new Set<string>([
  "manual",
  "hourly",
  "daily",
  "weekdays",
  "weekly",
  "monthly",
  "every",
  "folder",
  "connector",
  "webhook",
]);

/** The form's starting schedule: the task being edited, a draft the model proposed (anything the
 * form can't show falls back to a default), or blank. */
export function initialSchedule(task: ScheduledTask | null, draft: TaskDraft | undefined): ScheduleForm {
  const rule = task?.schedule;
  const draftKind = KNOWN.has(draft?.kind ?? "") ? (draft?.kind as ScheduleKind) : "manual";
  const kind = draft ? draftKind : rule?.kind === "once" ? "manual" : (rule?.kind ?? "manual");
  const at = draft ? draft.at : rule?.at;
  return {
    kind,
    time: kind !== "manual" && /^\d{1,2}:\d{2}$/.test(at ?? "") ? (at as string) : "09:00",
    weekday: (draft ? draft.weekday : rule?.weekday) ?? 0,
    date: initialDate(task, draft),
    minutes: rule?.minutes ?? 30,
    folder: rule?.folder ?? "",
    pattern: rule?.pattern && rule.pattern !== "*" ? rule.pattern : "",
    input: rule?.input ?? "",
    tool: rule?.tool ?? "",
    args: rule?.args ?? {},
    inputsFrom: rule?.inputs_from ?? {},
    perHour: rule?.per_hour ?? DEFAULT_PER_HOUR,
    trustUnmarked: rule?.trust_unmarked ?? false,
  };
}

/** The workflow's file inputs, which a new file in a folder can be given to. */
export function fileInputs(workflow: Workflow | null): string[] {
  return (workflow?.inputs ?? []).filter((input) => input.type === "file").map((input) => input.name);
}

/** What the form still needs before a task can start by itself, or null. */
export function scheduleProblem(form: ScheduleForm): string | null {
  if (form.kind === "folder" && !form.folder.trim()) return "Choose the folder to watch.";
  if (form.kind === "connector" && !form.tool) return "Pick what to ask the connector.";
  return null;
}

/** The schedule's part of what the form saves. */
export function schedulePayload(
  form: ScheduleForm,
  inputs: string[],
): Pick<CreateScheduledTaskPayload, "kind" | "at" | "weekday" | "day_of_month" | "start_date" | "watch"> {
  const { kind, time } = form;
  const fixedTime = kind === "daily" || kind === "weekdays" || kind === "weekly" || kind === "monthly";
  return {
    kind,
    at: fixedTime ? time : kind === "hourly" ? "00:00" : "",
    ...(kind === "weekly" ? { weekday: form.weekday } : {}),
    ...(kind === "monthly" ? { day_of_month: Number(form.date.split("-")[2]), start_date: form.date } : {}),
    ...(kind === "every" ? { watch: { minutes: form.minutes } } : {}),
    ...(kind === "folder"
      ? { watch: { folder: form.folder.trim(), pattern: form.pattern.trim() || "*", input: form.input || inputs[0] } }
      : {}),
    ...(kind === "connector"
      ? {
          watch: {
            minutes: form.minutes,
            tool: form.tool,
            args: form.args,
            inputs_from: form.inputsFrom,
            per_hour: form.perHour,
            trust_unmarked: form.trustUnmarked,
          },
        }
      : {}),
    ...(kind === "webhook" ? { watch: { inputs_from: form.inputsFrom, per_hour: form.perHour } } : {}),
  };
}

/** The saved webhook task a form edits, whose address it can show; a task not saved as one has none
 * yet (decision 0040). */
export function webhookTaskId(task: ScheduledTask | null): string | undefined {
  return task?.schedule.kind === "webhook" ? task.trigger_id : undefined;
}
