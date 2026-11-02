import type {
  CheckOp,
  Condition,
  Match,
  OnFailure,
  Operand,
  RecoveringStep,
  Workflow,
  WorkflowInput,
  WorkflowStep,
} from "../types/workflow";
import { failureFields, withFailure } from "./failureWords";
import { applyAskQuick, applyWaitQuick, askQuickFields, waitQuickFields } from "./pauseWords";
import { plainElement, plainReference } from "./plainSteps";
import { splitTemplate, wholeReference } from "./workflowLabels";
import { mapWorkflow } from "./workflowTree";

// The simple view's quick edit: every fixed value a step holds, in plain words, and nothing that
// changes the workflow's shape (which steps there are, what feeds what, code, a model's fields).
// A value that comes from an earlier step or an input is shown, not edited: changing where it comes
// from is a change of shape.

type QuickFieldKind = "text" | "longtext" | "number" | "list" | "lock" | "shown" | "pick";

export interface QuickField {
  key: string;
  label: string;
  kind: QuickFieldKind;
  /** text, longtext and shown: a string; number: a number; list: strings; lock: a boolean;
   * pick: one of `options`' values. */
  value: string | number | string[] | boolean;
  hint?: string;
  options?: { value: string | number; label: string }[];
  /** A heading the field starts, for a group of fields. */
  section?: string;
}

const ARG_LABEL: Record<string, string> = {
  url: "Web address",
  path: "File location",
  text: "Text it types",
  values: "Option it picks",
  query: "What it looks for",
  content: "What it writes",
  to: "Send to",
  subject: "Subject",
  body: "Message",
  filename: "File name",
  sheet: "Sheet",
  ref: "On the page",
};

// Arguments a person can't sensibly change without the page or the code in front of them.
const SHOWN_ARGS = new Set(["ref", "element", "script", "code", "description"]);

const OP_WORDS: Record<CheckOp, string> = {
  eq: "is",
  ne: "isn’t",
  gt: "is more than",
  ge: "is at least",
  lt: "is less than",
  le: "is at most",
  contains: "contains",
  not_contains: "doesn’t contain",
  starts_with: "starts with",
  ends_with: "ends with",
  not_empty: "isn’t empty",
  empty: "is empty",
  before: "is before",
  after: "is after",
};

function words(name: string): string {
  const spaced = name.replace(/_/g, " ");
  return spaced.charAt(0).toUpperCase() + spaced.slice(1);
}

/** A template as words: references named, the rest kept. */
function plainTemplate(text: string, inputs: WorkflowInput[]): string {
  return splitTemplate(text)
    .map((part) => ("ref" in part ? `[${plainReference(part.ref, inputs).replace(/[“”]/g, "")}]` : part.text))
    .join("");
}

function isFixed(value: unknown): boolean {
  if (typeof value === "number" || typeof value === "boolean") return true;
  if (Array.isArray(value)) return value.every((item) => typeof item === "string" && !item.includes("{{"));
  return typeof value === "string" && !value.includes("{{");
}

function argField(name: string, value: unknown, inputs: WorkflowInput[]): QuickField {
  const label = ARG_LABEL[name] ?? words(name);
  const key = `arg:${name}`;
  if (name === "ref") return { key, label, kind: "shown", value: plainElement(value, inputs) };
  if (SHOWN_ARGS.has(name) || !isFixed(value)) {
    const ref = wholeReference(value);
    const shown =
      ref !== null
        ? `Comes from ${plainReference(ref, inputs)}`
        : typeof value === "string"
          ? plainTemplate(value, inputs)
          : JSON.stringify(value);
    return { key, label, kind: "shown", value: shown };
  }
  if (typeof value === "number") return { key, label, kind: "number", value };
  if (Array.isArray(value)) return { key, label, kind: "list", value: value as string[] };
  if (typeof value === "boolean") return { key, label, kind: "shown", value: value ? "Yes" : "No" };
  const text = String(value);
  return { key, label, kind: text.length > 80 || text.includes("\n") ? "longtext" : "text", value: text };
}

function operandWords(operand: Operand, inputs: WorkflowInput[]): string {
  if ("ref" in operand) return plainReference(operand.ref, inputs);
  if ("count" in operand) return `the number of ${plainReference(operand.count, inputs)}`;
  return JSON.stringify(operand.value);
}

/** One field per condition whose right side is a fixed value; the rest of the sentence is its label. */
function conditionFields(
  prefix: string,
  conditions: Condition[],
  match: Match | undefined,
  inputs: WorkflowInput[],
): QuickField[] {
  return conditions.map((condition, index) => {
    const lead = index === 0 ? "If" : match === "any" ? "Or if" : "And if";
    const sentence = `${lead} ${operandWords(condition.left, inputs)} ${OP_WORDS[condition.op]}`;
    const key = `${prefix}:${index}`;
    const right = condition.right;
    if (!right || !("value" in right)) {
      const rest = right ? ` ${operandWords(right, inputs)}` : "";
      return { key, label: "Condition", kind: "shown", value: sentence + rest };
    }
    if (typeof right.value === "number") return { key, label: sentence, kind: "number", value: right.value };
    return { key, label: sentence, kind: "text", value: String(right.value) };
  });
}

function lockField(irreversible: boolean): QuickField {
  return {
    key: "irreversible",
    label: "Can’t be undone",
    kind: "lock",
    value: irreversible,
    hint: irreversible
      ? "A test run stops before this step. Only the full editor can unmark it."
      : "Mark it if it sends, submits, pays or deletes something.",
  };
}

/** What the quick edit shows for a step, title first. */
export function quickFields(step: WorkflowStep, inputs: WorkflowInput[]): QuickField[] {
  const fields: QuickField[] = [{ key: "title", label: "Name", kind: "text", value: step.title }];
  switch (step.kind) {
    case "tool":
      return [
        ...fields,
        ...Object.entries(step.args).map(([name, value]) => argField(name, value, inputs)),
        lockField(step.irreversible),
        ...failureFields(step),
      ];
    case "script":
      return [
        ...fields,
        ...Object.entries(step.inputs).map(([name, value]) => argField(name, value, inputs)),
        { key: "code", label: "Program", kind: "shown", value: "Changed in the full editor" },
        ...failureFields(step),
      ];
    case "llm":
      return [
        ...fields,
        { key: "prompt", label: "What it asks the AI", kind: "longtext", value: step.prompt },
        ...failureFields(step),
      ];
    case "agent":
      return [
        ...fields,
        { key: "goal", label: "What it should do", kind: "longtext", value: step.goal },
        { key: "max_steps", label: "Most tries", kind: "number", value: step.max_steps, hint: "AI calls, 1 to 60" },
        { key: "sites", label: "Websites it may open", kind: "list", value: step.sites },
        { key: "folders", label: "Folders it may change", kind: "list", value: step.folders },
        lockField(step.irreversible),
        ...failureFields(step),
      ];
    case "check":
      return [...fields, ...conditionFields("cond", step.conditions, step.match, inputs)];
    case "approval":
      return [
        ...fields,
        { key: "message", label: "What it asks you", kind: "longtext", value: step.message },
        ...conditionFields("cond", step.when, step.match, inputs),
      ];
    case "ask":
      return [...fields, ...askQuickFields(step, inputs)];
    case "wait":
      return [...fields, ...waitQuickFields(step, inputs)];
    case "branch":
      return [...fields, ...conditionFields("cond", step.conditions, step.match, inputs)];
    case "choice":
      return [
        ...fields,
        ...step.cases.map(
          (c, index): QuickField => ({
            key: `case:${index}`,
            label: `Path ${index + 1}, when ${plainReference(step.value, inputs)} is`,
            kind: "text",
            value: c.is,
          }),
        ),
      ];
    case "loop":
      return [
        ...fields,
        {
          key: "max_items",
          label: "Most items",
          kind: "number",
          value: step.max_items,
          hint: "1 to 200. A longer list stops the run.",
        },
        {
          key: "on_item_failure",
          label: "If one item fails",
          kind: "pick",
          value: step.on_item_failure ?? "stop",
          options: [
            { value: "stop", label: "Stop the run" },
            { value: "skip", label: "Skip that item and go on" },
          ],
          hint: "Skipped items are listed in the run’s report.",
        },
        ...conditionFields("cond", step.until ?? [], step.match, inputs).map((field) => ({
          ...field,
          label: field.label.replace(/^(If|And if|Or if)/, (lead) => `Stop early ${lead.toLowerCase()}`),
        })),
      ];
  }
}

function setRight(conditions: Condition[], at: string, value: unknown): Condition[] {
  return conditions.map((c, i) => (i === Number(at) ? { ...c, right: { value } } : c));
}

/** `step` with one quick field changed. */
export function applyQuick(step: WorkflowStep, key: string, value: QuickField["value"]): WorkflowStep {
  const [head, rest] = key.split(/:(.*)/s);
  if (head === "title") return { ...step, title: String(value) };
  if (head === "irreversible" && (step.kind === "tool" || step.kind === "agent")) {
    // On only: unmarking a step that can't be undone is the full editor's, on purpose. Once
    // marked it is never tried again on its own.
    const marked = { ...step, irreversible: step.irreversible || value === true };
    return marked.irreversible ? withFailure(marked, { retries: 0 }) : marked;
  }
  if (head === "failure") return withFailure(step as RecoveringStep, { [rest]: value } as Partial<OnFailure>);
  switch (step.kind) {
    case "tool":
      return head === "arg" ? { ...step, args: { ...step.args, [rest]: value } } : step;
    case "script":
      return head === "arg" ? { ...step, inputs: { ...step.inputs, [rest]: value } } : step;
    case "llm":
      return head === "prompt" ? { ...step, prompt: String(value) } : step;
    case "agent":
      if (head === "goal") return { ...step, goal: String(value) };
      if (head === "max_steps") return { ...step, max_steps: Number(value) };
      if (head === "sites" || head === "folders") return { ...step, [head]: value as string[] };
      return step;
    case "check":
    case "branch":
      return head === "cond" ? { ...step, conditions: setRight(step.conditions, rest, value) } : step;
    case "approval":
      if (head === "message") return { ...step, message: String(value) };
      return head === "cond" ? { ...step, when: setRight(step.when, rest, value) } : step;
    case "ask":
      return applyAskQuick(step, key, value);
    case "wait":
      return applyWaitQuick(step, key, value);
    case "choice":
      if (head !== "case") return step;
      return { ...step, cases: step.cases.map((c, i) => (i === Number(rest) ? { ...c, is: String(value) } : c)) };
    case "loop":
      if (head === "cond") return { ...step, until: setRight(step.until ?? [], rest, value) };
      if (head === "on_item_failure") return { ...step, on_item_failure: value === "skip" ? "skip" : "stop" };
      return head === "max_items" ? { ...step, max_items: Number(value) } : step;
  }
}

/** The workflow with step `id` replaced. */
export function replaceStep(workflow: Workflow, id: string, next: WorkflowStep): Workflow {
  return mapWorkflow(workflow, (step) => (step.id === id ? next : step));
}
