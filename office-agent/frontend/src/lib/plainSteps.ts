import type { AskStep, MemoryEntry, WaitStep, WorkflowInput, WorkflowStep } from "../types/workflow";
import { toolLabel } from "./toolLabels";
import { splitTemplate, wholeReference } from "./workflowLabels";

// The simple view says what a step does in words a person would use: no tool names, no variable
// names, no code. Where a value comes from an earlier step it reads "the claim's name"; where it
// comes from an input, the input's label.

const FIELD_CHARS = 32;

function words(name: string): string {
  return name.replace(/_/g, " ");
}

/** What a task remembers and when its run started (decision 0034), in words. */
function memoryWords(head: string, rest: string[]): string | null {
  if (head === "memory" && rest.length === 1) return `the remembered “${words(rest[0])}”`;
  if (head === "run" && rest[0] === "started_at") return "when this run started";
  if (head === "run" && rest[0] === "date") return "this run’s day";
  return null;
}

/** "claim.employee_id" -> "the claim's employee id"; an input -> its label. */
export function plainReference(ref: string, inputs: WorkflowInput[]): string {
  const [head, ...rest] = ref.split(".");
  const input = inputs.find((i) => i.name === head);
  const own = input ? null : memoryWords(head, rest);
  if (own) return own;
  const base = input ? input.label || words(head) : `the ${words(head)}`;
  if (rest.length === 0) return input ? `“${base}”` : base;
  return `${base}${base.endsWith("s") ? "’" : "’s"} ${rest.map(words).join(" ")}`;
}

/** A value as words: a reference is named, plain text is quoted. */
function plainValue(value: unknown, inputs: WorkflowInput[]): string {
  if (typeof value !== "string") return "a value";
  const ref = wholeReference(value);
  if (ref) return plainReference(ref, inputs);
  // Inside quoted text a reference is a placeholder, so it takes brackets rather than more quotes.
  const text = splitTemplate(value)
    .map((part) => ("ref" in part ? `[${plainReference(part.ref, inputs).replace(/[“”]/g, "")}]` : part.text))
    .join("")
    .trim();
  return text.length > FIELD_CHARS ? `“${text.slice(0, FIELD_CHARS)}…”` : `“${text}”`;
}

const ROLE_WORD: Record<string, string> = {
  textbox: "box",
  button: "button",
  combobox: "list",
  listbox: "list",
  checkbox: "checkbox",
  radio: "option",
  link: "link",
};

/** `button "Submit claim"` -> The “Submit claim” button: what a step acts on, as a person names it. */
export function plainElement(ref: unknown, inputs: WorkflowInput[]): string {
  const role = typeof ref === "string" ? (/^(\w+)/.exec(ref)?.[1] ?? "") : "";
  const name = fieldName(ref, inputs);
  return ROLE_WORD[role] ? `The ${name} ${ROLE_WORD[role]}` : name;
}

/** `textbox "Full name"` -> “Full name”: the name a person sees on the page. */
function fieldName(ref: unknown, inputs: WorkflowInput[]): string {
  if (typeof ref !== "string") return "a field";
  let quoted = /"(.*)"/.exec(ref)?.[1];
  if (!quoted) return "a field";
  // A dropdown's name on the page runs its label into its options: keep the label.
  if (/^(combobox|listbox)\b/.test(ref)) quoted = quoted.split(/(?:Choose|Select)\W/)[0].trim() || quoted;
  return plainValue(quoted, inputs);
}

function site(url: unknown): string {
  if (typeof url !== "string") return "a web page";
  if (url.includes("{{")) return "a web page";
  try {
    const parsed = new URL(url);
    return `${parsed.host}${parsed.pathname === "/" ? "" : parsed.pathname}`;
  } catch {
    return "a web page";
  }
}

function toolSentence(tool: string, args: Record<string, unknown>, inputs: WorkflowInput[]): string {
  const value = (key: string) => plainValue(args[key], inputs);
  switch (tool) {
    case "browser_navigate":
      return `Opens ${site(args.url)}`;
    case "browser_type":
      return `Types ${value("text")} into ${fieldName(args.ref, inputs)}`;
    case "browser_click":
      return `Clicks ${fieldName(args.ref, inputs)}`;
    case "browser_select_option": {
      const picked = Array.isArray(args.values) ? args.values[0] : args.values;
      return `Picks ${plainValue(picked, inputs)} in ${fieldName(args.ref, inputs)}`;
    }
    case "browser_wait_for":
      return `Waits for the page to show ${value("text")}`;
    case "browser_evaluate":
      return "Works with the page directly";
    case "read_file":
      return `Reads ${value("path")}`;
    case "write_file":
      return `Saves ${value("path")}`;
    case "list_files":
      return `Lists the files in ${value("path")}`;
    default:
      return toolLabel(tool);
  }
}

function listWords(items: string[]): string {
  if (items.length <= 1) return items.join("");
  return `${items.slice(0, -1).join(", ")} and ${items[items.length - 1]}`;
}

function askSentence(step: AskStep): string {
  const named = step.fields.map((f) => `“${f.label || words(f.name)}”`);
  const shown = named.length > 3 ? [...named.slice(0, 2), `${named.length - 2} more`] : named;
  const then = step.on_timeout === "defaults" ? "goes on with the defaults" : "the run stops";
  const timeout = step.timeout_hours ? `; if no one answers in ${duration(Math.round(step.timeout_hours * 60))}, ${then}` : "";
  return `Asks you for ${listWords(shown)}${timeout}`;
}

/** "Waits 10 minutes", "Waits until 17:00", "Waits for “done.xlsx” to appear". */
function waitSentence(step: WaitStep, inputs: WorkflowInput[]): string {
  if (step.until === "duration") return `Waits ${duration(step.minutes ?? 0)}`;
  if (step.until === "time") {
    const day = step.on ? ` on ${plainDay(step.on, inputs)}` : "";
    return `Waits until ${step.at ?? "a time"}${day}`;
  }
  return `Waits up to ${duration(step.max_minutes ?? 1440)} for ${plainValue(step.path ?? "", inputs)} to appear`;
}

const DAY_WORDS: Record<string, string> = {
  today: "today",
  yesterday: "yesterday",
  week_start: "Monday this week",
  month_start: "the 1st of this month",
};

function plainDay(on: string, inputs: WorkflowInput[]): string {
  return DAY_WORDS[on] ?? plainValue(on.includes("{{") || /^\d/.test(on) ? on : `{{${on}}}`, inputs);
}

/** 90 -> "1 hour 30 minutes", 2880 -> "2 days". */
export function duration(minutes: number): string {
  const plural = (n: number, unit: string) => `${n} ${unit}${n === 1 ? "" : "s"}`;
  if (minutes >= 1440 && minutes % 1440 === 0) return plural(minutes / 1440, "day");
  if (minutes >= 60) {
    const rest = minutes % 60;
    return rest ? `${plural(Math.floor(minutes / 60), "hour")} ${plural(rest, "minute")}` : plural(minutes / 60, "hour");
  }
  return plural(minutes, "minute");
}

/** One sentence on what a step does, or null when its title already says all there is.
 * `taskNames`: the saved tasks by id, for a step that runs one (decision 0035). */
export function plainDetail(
  step: WorkflowStep,
  inputs: WorkflowInput[],
  memory: MemoryEntry[] = [],
  taskNames: Map<string, string> = new Map(),
): string | null {
  switch (step.kind) {
    case "tool":
      return toolSentence(step.tool, step.args, inputs);
    case "script":
      return "Runs a small program on this computer";
    case "llm":
      return "AI reads what came before and writes the result";
    case "agent":
      return step.autonomy === "bounded"
        ? "AI works it out with the tools it was given"
        : "AI works it out its own way";
    case "check":
      return step.otherwise === "end" ? "Ends the run quietly if this isn’t so" : "Stops the run if this isn’t so";
    case "approval":
      return "Waits for your OK before going on";
    case "ask":
      return askSentence(step);
    case "wait":
      return waitSentence(step, inputs);
    case "remember": {
      const label = memory.find((entry) => entry.name === step.name)?.label;
      return `Keeps “${label || words(step.name)}” for the next run`;
    }
    case "run_task": {
      const name = taskNames.get(step.task);
      return name ? `Runs your task “${name}” and waits for it to finish` : "Runs another of your tasks";
    }
    case "branch":
    case "loop":
      return null;
    case "choice":
      return `Goes one way by ${plainReference(step.value, inputs)}`;
  }
}

/** What kind of thing a step is, in a word or two. */
export function plainKind(step: WorkflowStep): string {
  switch (step.kind) {
    case "tool":
      if (step.tool.startsWith("browser_")) return "Website";
      if (/(file|xlsx|docx|pptx|pdf)/.test(step.tool)) return "File";
      return "Action";
    case "script":
      return "Program";
    case "llm":
    case "agent":
      return "AI";
    case "check":
      return "Check";
    case "approval":
      return "Your OK";
    case "ask":
      return "Your answer";
    case "wait":
      return "Wait";
    case "remember":
      return "Memory";
    case "run_task":
      return "Task";
    case "branch":
      return "If";
    case "choice":
      return "Paths";
    case "loop":
      return "Repeat";
  }
}
