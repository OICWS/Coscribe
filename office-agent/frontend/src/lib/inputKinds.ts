import type { WorkflowInput } from "../types/workflow";

// Mirrors workflow_spec/inputs.py: the kinds of value a workflow asks for at each run, and the
// dates a date input can default to, worked out on the day each run starts.

export const INPUT_TYPE_LABEL: Record<WorkflowInput["type"], string> = {
  text: "Text",
  number: "Number",
  date: "Date",
  choice: "Choice",
  yes_no: "Yes or no",
  file: "File",
  folder: "Folder",
};

export const RELATIVE_DATES = [
  ["today", "Today"],
  ["yesterday", "Yesterday"],
  ["week_start", "Monday this week"],
  ["last_week_start", "Monday last week"],
  ["last_week_end", "Sunday last week"],
  ["month_start", "First day of this month"],
  ["last_month_start", "First day of last month"],
  ["last_month_end", "Last day of last month"],
  ["year_start", "First day of this year"],
] as const;

export type RelativeDate = (typeof RELATIVE_DATES)[number][0];

const RELATIVE_LABEL = Object.fromEntries(RELATIVE_DATES) as Record<RelativeDate, string>;

export function isRelativeDate(value: unknown): value is RelativeDate {
  return typeof value === "string" && value in RELATIVE_LABEL;
}

function iso(date: Date): string {
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}

/** The date a relative default stands for on `today`. */
export function resolveDate(value: RelativeDate, today: Date = new Date()): string {
  const y = today.getFullYear();
  const m = today.getMonth();
  const d = today.getDate();
  const monday = d - ((today.getDay() + 6) % 7);
  switch (value) {
    case "today":
      return iso(new Date(y, m, d));
    case "yesterday":
      return iso(new Date(y, m, d - 1));
    case "week_start":
      return iso(new Date(y, m, monday));
    case "last_week_start":
      return iso(new Date(y, m, monday - 7));
    case "last_week_end":
      return iso(new Date(y, m, monday - 1));
    case "month_start":
      return iso(new Date(y, m, 1));
    case "last_month_start":
      return iso(new Date(y, m - 1, 1));
    case "last_month_end":
      return iso(new Date(y, m, 0));
    case "year_start":
      return iso(new Date(y, 0, 1));
  }
}

/** An input's usual value in words: "First day of last month", "Yes", the text itself. */
export function plainDefault(input: WorkflowInput): string | null {
  const value = input.default;
  if (value === null || value === "") return null;
  if (input.type === "date" && isRelativeDate(value)) return RELATIVE_LABEL[value];
  if (input.type === "yes_no") return value === true || value === "yes" ? "Yes" : "No";
  return String(value);
}

/** The value a run starts with when the person doesn't change it. */
export function startingValue(input: WorkflowInput, today?: Date): string {
  if (input.default === null) return "";
  if (input.type === "date" && isRelativeDate(input.default)) return resolveDate(input.default, today);
  if (input.type === "yes_no") return input.default === true || input.default === "yes" ? "yes" : "no";
  return String(input.default);
}
