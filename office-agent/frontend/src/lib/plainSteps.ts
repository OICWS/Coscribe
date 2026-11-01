import type { WorkflowInput, WorkflowStep } from "../types/workflow";
import { toolLabel } from "./toolLabels";
import { splitTemplate, wholeReference } from "./workflowLabels";

// The simple view says what a step does in words a person would use: no tool names, no variable
// names, no code. Where a value comes from an earlier step it reads "the claim's name"; where it
// comes from an input, the input's label.

const FIELD_CHARS = 32;

function words(name: string): string {
  return name.replace(/_/g, " ");
}

/** "claim.employee_id" -> "the claim's employee id"; an input -> its label. */
export function plainReference(ref: string, inputs: WorkflowInput[]): string {
  const [head, ...rest] = ref.split(".");
  const input = inputs.find((i) => i.name === head);
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

/** One sentence on what a step does, or null when its title already says all there is. */
export function plainDetail(step: WorkflowStep, inputs: WorkflowInput[]): string | null {
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
      return "Stops the run if this isn’t so";
    case "approval":
      return "Waits for your OK before going on";
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
    case "branch":
      return "If";
    case "choice":
      return "Paths";
    case "loop":
      return "Repeat";
  }
}
