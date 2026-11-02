import type { AskField, AskStep, WaitStep, WorkflowInput } from "../types/workflow";
import { INPUT_TYPE_LABEL } from "./inputKinds";
import { duration, plainReference } from "./plainSteps";
import type { QuickField } from "./quickEdit";
import { splitTemplate, wholeReference } from "./workflowLabels";

// Words and quick-edit fields for the steps that pause a run (decision 0033): one that asks you
// for values, and one that waits for a time or a file.

/** How long an ask step waits for you, and what then: "waits until you answer". */
export function askTimeoutWords(step: AskStep): string {
  if (step.timeout_hours == null) return "waits until you answer";
  const after = `after ${duration(Math.round(step.timeout_hours * 60))}`;
  return `${after}, ${step.on_timeout === "defaults" ? "goes on with the defaults" : "stops the run"}`;
}

/** Whether every value it needs has a default, so it can go on without you. */
export function hasEveryDefault(step: AskStep): boolean {
  return step.fields.every((f) => f.required === false || (f.default != null && f.default !== ""));
}

export const TIMEOUTS = [
  { value: 0, label: "Until you answer" },
  { value: 1, label: "1 hour" },
  { value: 4, label: "4 hours" },
  { value: 24, label: "1 day" },
  { value: 72, label: "3 days" },
  { value: 168, label: "1 week" },
];

export const FIELD_TYPE_LABEL: Record<AskField["type"], string> = { ...INPUT_TYPE_LABEL, pick: "Pick from a list" };

function askFieldQuick(field: AskField, index: number, inputs: WorkflowInput[]): QuickField[] {
  const section = `Asks for: ${field.label || field.name}`;
  const label: QuickField = { key: `field:${index}:label`, label: "What it’s called", kind: "text", value: field.label, section };
  if (field.type === "choice") {
    return [label, { key: `field:${index}:options`, label: "Options", kind: "list", value: field.options ?? [] }];
  }
  if (field.type === "pick") {
    const from = field.items ? plainReference(field.items, inputs) : "a list";
    return [label, { key: `field:${index}:items`, label: "Picked from", kind: "shown", value: `Items of ${from}` }];
  }
  return [label, { key: `field:${index}:type`, label: "Kind", kind: "shown", value: FIELD_TYPE_LABEL[field.type] }];
}

export function askQuickFields(step: AskStep, inputs: WorkflowInput[]): QuickField[] {
  const hours = step.timeout_hours ?? 0;
  const options = TIMEOUTS.some((t) => t.value === hours) ? TIMEOUTS : [...TIMEOUTS, { value: hours, label: `${hours} hours` }];
  const timeout: QuickField[] = [
    { key: "timeout_hours", label: "How long it waits for you", kind: "pick", value: hours, options, section: "If no one answers" },
  ];
  if (hours > 0) {
    const defaults = hasEveryDefault(step);
    timeout.push({
      key: "on_timeout",
      label: "Then",
      kind: "pick",
      value: step.on_timeout ?? "fail",
      options: [
        { value: "fail", label: "Stop the run" },
        ...(defaults ? [{ value: "defaults", label: "Go on with the defaults" }] : []),
      ],
      hint: defaults ? undefined : "Going on needs a default for every value; set them in the full editor.",
    });
  }
  return [
    { key: "message", label: "What it asks you", kind: "longtext", value: step.message },
    ...step.fields.flatMap((field, index) => askFieldQuick(field, index, inputs)),
    ...timeout,
  ];
}

export function applyAskQuick(step: AskStep, key: string, value: QuickField["value"]): AskStep {
  const [head, rest] = key.split(/:(.*)/s);
  if (head === "message") return { ...step, message: String(value) };
  if (head === "timeout_hours") {
    const hours = Number(value);
    return hours > 0 ? { ...step, timeout_hours: hours } : { ...step, timeout_hours: null, on_timeout: "fail" };
  }
  if (head === "on_timeout") return { ...step, on_timeout: value === "defaults" ? "defaults" : "fail" };
  if (head !== "field") return step;
  const [at, part] = rest.split(":");
  const fields = step.fields.map((f, i) => {
    if (i !== Number(at)) return f;
    if (part === "label") return { ...f, label: String(value) };
    return part === "options" ? { ...f, options: value as string[] } : f;
  });
  return { ...step, fields };
}

const DAYS = [
  { value: "", label: "The next time it comes" },
  { value: "today", label: "Today" },
  { value: "week_start", label: "Monday this week" },
  { value: "month_start", label: "The 1st of this month" },
];

/** A template as words: "bank/[Month].csv". */
function templateWords(text: string, inputs: WorkflowInput[]): string {
  return splitTemplate(text)
    .map((part) => ("ref" in part ? `[${plainReference(part.ref, inputs).replace(/[“”]/g, "")}]` : part.text))
    .join("");
}

export function waitQuickFields(step: WaitStep, inputs: WorkflowInput[]): QuickField[] {
  if (step.until === "duration") {
    return [{ key: "minutes", label: "How long, in minutes", kind: "number", value: step.minutes ?? 10, hint: `${duration(step.minutes ?? 10)}, at most a week` }];
  }
  if (step.until === "time") {
    const on = step.on ?? "";
    const fixed = DAYS.some((d) => d.value === on);
    return [
      { key: "at", label: "Time", kind: "text", value: step.at ?? "", hint: "Like 17:00" },
      fixed
        ? { key: "on", label: "On", kind: "pick", value: on, options: DAYS }
        : { key: "on", label: "On", kind: "shown", value: wholeReference(on) ? plainReference(wholeReference(on) ?? "", inputs) : on },
    ];
  }
  const path = step.path ?? "";
  return [
    path.includes("{{")
      ? { key: "path", label: "File", kind: "shown", value: templateWords(path, inputs) }
      : { key: "path", label: "File", kind: "text", value: path },
    { key: "max_hours", label: "Longest wait, in hours", kind: "number", value: (step.max_minutes ?? 1440) / 60, hint: "At most a week" },
    {
      key: "if_missing",
      label: "If it doesn’t come",
      kind: "pick",
      value: step.if_missing ?? "fail",
      options: [
        { value: "fail", label: "Stop the run" },
        { value: "continue", label: "Go on without it" },
      ],
    },
  ];
}

export function applyWaitQuick(step: WaitStep, key: string, value: QuickField["value"]): WaitStep {
  switch (key) {
    case "minutes":
      return { ...step, minutes: Math.max(1, Math.min(10080, Math.round(Number(value)))) };
    case "max_hours":
      return { ...step, max_minutes: Math.max(1, Math.min(10080, Math.round(Number(value) * 60))) };
    case "at":
    case "path":
      return { ...step, [key]: String(value) };
    case "on":
      return { ...step, on: value ? String(value) : null };
    case "if_missing":
      return { ...step, if_missing: value === "continue" ? "continue" : "fail" };
    default:
      return step;
  }
}

/** When a pause ends, as a person says it: "today at 17:00", "tomorrow at 09:00", "Tue 4 Nov at 09:00". */
export function untilWords(iso: string, now: Date = new Date()): string {
  const when = new Date(iso);
  if (Number.isNaN(when.getTime())) return iso;
  const time = when.toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" });
  const day = (d: Date) => new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime();
  const days = Math.round((day(when) - day(now)) / 86_400_000);
  if (days === 0) return `today at ${time}`;
  if (days === 1) return `tomorrow at ${time}`;
  const date = when.toLocaleDateString("en-GB", { weekday: "short", day: "numeric", month: "short" });
  return `${date} at ${time}`;
}

function answerWords(value: unknown): string {
  if (Array.isArray(value)) return `${value.length} picked`;
  if (value === true) return "yes";
  if (value === false) return "no";
  return value === null || value === undefined || value === "" ? "blank" : String(value);
}

/** A finished ask step's row: what was answered, the first two values. */
export function answeredWords(step: AskStep, output: unknown, note: string | null | undefined): string {
  const values = typeof output === "object" && output !== null ? (output as Record<string, unknown>) : {};
  const shown = step.fields.slice(0, 2).map((f) => `${f.label || f.name}: ${answerWords(values[f.name])}`);
  return [note || "Answered", ...shown].join(" · ");
}

/** A finished wait step's row. */
export function waitedWords(step: WaitStep, output: unknown): string {
  if (step.until === "duration") return `Waited ${duration(step.minutes ?? 0)}`;
  if (step.until === "time") return `Waited until ${step.at ?? "the time"}`;
  const found = typeof output === "object" && output !== null && (output as { found?: unknown }).found === true;
  return found ? "The file came" : "The file didn’t come · went on without it";
}
