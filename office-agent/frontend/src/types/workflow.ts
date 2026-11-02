// Mirrors src/coscribe/workflow_spec/spec.py (the definition) and
// engine.py's StepRecord (one step of one run), which comes from wire.gen.ts.

import type { WorkflowCheck, WorkflowStepRecord } from "./wire.gen";

export type StepKind =
  | "tool"
  | "script"
  | "llm"
  | "agent"
  | "check"
  | "approval"
  | "ask"
  | "wait"
  | "remember"
  | "branch"
  | "choice"
  | "loop";
export type Autonomy = "bounded" | "high" | "full";
export type OutputFieldType = "text" | "number" | "boolean" | "list";
export type CheckOp =
  | "eq"
  | "ne"
  | "gt"
  | "ge"
  | "lt"
  | "le"
  | "contains"
  | "not_contains"
  | "starts_with"
  | "ends_with"
  | "not_empty"
  | "empty"
  | "before"
  | "after";
/** Whether every condition must hold, or one is enough. */
export type Match = "all" | "any";

/** Exactly one key is present. */
export type Operand = { ref: string } | { count: string } | { value: unknown };

export interface Condition {
  left: Operand;
  op: CheckOp;
  right?: Operand | null;
}

export interface WorkflowInput {
  name: string;
  label: string;
  type: "text" | "number" | "date" | "choice" | "yes_no" | "file" | "folder";
  /** A date's may be relative ("last_month_start", lib/inputKinds.ts), worked out per run. */
  default: string | number | boolean | null;
  /** A choice's options, in order. */
  options?: string[];
  /** Absent means required. */
  required?: boolean;
}

export interface OutputField {
  name: string;
  type: OutputFieldType;
  description: string;
}

interface StepBase {
  id: string;
  title: string;
}

/** What a step does when it still fails (decision 0032): try again, then stop, skip it, or run
 * `steps` in its place. Absent: stop at once. */
export interface OnFailure {
  /** 0 to 5; always 0 for a step that can't be undone. */
  retries: number;
  /** Between tries, 0 to 300. */
  wait_seconds: number;
  then: "stop" | "skip" | "steps";
  /** Run in its place when `then` is "steps"; they read `failure` ({ step, message }). */
  steps: WorkflowStep[];
}

/** A step whose work can fail for reasons outside the workflow. */
interface RecoveringBase extends StepBase {
  on_failure?: OnFailure | null;
}

export interface ToolStep extends RecoveringBase {
  kind: "tool";
  tool: string;
  args: Record<string, unknown>;
  save_as: string | null;
  /** Sends, submits, pays or deletes outside this machine: a test stops before it. */
  irreversible: boolean;
}

export interface ScriptStep extends RecoveringBase {
  kind: "script";
  code: string;
  inputs: Record<string, unknown>;
  save_as: string | null;
}

export interface LLMStep extends RecoveringBase {
  kind: "llm";
  prompt: string;
  fields: OutputField[];
  model: string | null;
  save_as: string;
}

/** Decision 0028. "bounded" may use only `tools`, `folders` and `sites`. */
export interface AgentStep extends RecoveringBase {
  kind: "agent";
  autonomy: Autonomy;
  goal: string;
  tools: string[];
  folders: string[];
  sites: string[];
  /** Empty means the result is { report: <the agent's reply> }. */
  fields: OutputField[];
  max_steps: number;
  model: string | null;
  save_as: string | null;
  /** The person said what this step reads from outside may be acted on. */
  trusted_input: boolean;
  /** As a tool step's. */
  irreversible: boolean;
}

export interface CheckStep extends StepBase {
  kind: "check";
  conditions: Condition[];
  /** Absent: all. */
  match?: Match;
  /** When the conditions don't hold: fail the run, or end it as done with nothing to do (decision
   * 0034; only outside loops and branches). Absent: fail. */
  otherwise?: "fail" | "end";
}

export interface ApprovalStep extends StepBase {
  kind: "approval";
  message: string;
  /** Empty: always pause. */
  when: Condition[];
  /** Absent: all. */
  match?: Match;
}

/** One value an ask step asks for (decision 0033): an input's kinds, or `pick`, some items of a list. */
export interface AskField {
  name: string;
  label: string;
  type: WorkflowInput["type"] | "pick";
  options?: string[];
  default?: string | number | boolean | null;
  /** Absent means required. */
  required?: boolean;
  /** A pick's list, by reference. */
  items?: string | null;
  /** A pick's field of each item to show. Empty: the item itself. */
  show?: string;
}

/** Pauses until a person fills `fields`; `save_as` gets { name: value }. */
export interface AskStep extends StepBase {
  kind: "ask";
  message: string;
  fields: AskField[];
  save_as: string;
  /** Null or absent: it waits for as long as it takes. */
  timeout_hours?: number | null;
  /** After the timeout: go on with the defaults, or fail. Absent: fail. */
  on_timeout?: "defaults" | "fail";
}

/** Pauses the run, holding nothing: for `minutes`, until `at` (HH:MM) on the day `on`, or until
 * `path` exists, for at most `max_minutes`. */
export interface WaitStep extends StepBase {
  kind: "wait";
  until: "duration" | "time" | "file";
  minutes?: number | null;
  /** "17:00". */
  at?: string | null;
  /** A date, a relative one ("today") or a reference. Absent: the next time `at` comes. */
  on?: string | null;
  path?: string | null;
  /** A file's longest wait. Absent: a day. */
  max_minutes?: number;
  /** A file that doesn't come: fail, or go on. Absent: fail. */
  if_missing?: "fail" | "continue";
  /** A file's: { path, found }. */
  save_as?: string | null;
}

/** Keeps `value` as the memory `name` for the next run (decision 0034), once this run finishes. */
export interface RememberStep extends StepBase {
  kind: "remember";
  name: string;
  value: string;
}

/** One value a task keeps from one run to the next, read as {{memory.<name>}}. */
export interface MemoryEntry {
  name: string;
  label: string;
  type: "text" | "number" | "date" | "list";
  /** What the first run reads. */
  initial?: unknown;
}

export interface BranchStep extends StepBase {
  kind: "branch";
  conditions: Condition[];
  /** Absent: all. */
  match?: Match;
  then: WorkflowStep[];
  otherwise: WorkflowStep[];
}

/** One of several paths, by a value: the first case it equals, else `otherwise`. */
interface ChoiceCase {
  is: string;
  steps: WorkflowStep[];
}

export interface ChoiceStep extends StepBase {
  kind: "choice";
  /** A reference to the value that picks the path. */
  value: string;
  cases: ChoiceCase[];
  otherwise: WorkflowStep[];
}

export interface LoopStep extends StepBase {
  kind: "loop";
  /** A reference to the list to go through. */
  over: string;
  item: string;
  steps: WorkflowStep[];
  /** What to keep from each pass; the list of them is saved as save_as. */
  collect: string | null;
  save_as: string | null;
  max_items: number;
  /** Checked after each pass; when they hold, the loop ends early. Empty: it goes through every item. */
  until?: Condition[];
  /** Absent: all. */
  match?: Match;
  /** A pass that fails: stop the run, or skip that item and go on. Absent: stop. */
  on_item_failure?: "stop" | "skip";
}

export type WorkflowStep =
  | ToolStep
  | ScriptStep
  | LLMStep
  | AgentStep
  | CheckStep
  | ApprovalStep
  | AskStep
  | WaitStep
  | RememberStep
  | BranchStep
  | ChoiceStep
  | LoopStep;
export type BlockStep = BranchStep | ChoiceStep | LoopStep;
export type RecoveringStep = ToolStep | ScriptStep | LLMStep | AgentStep;

/** Decision 0030: one switch per task, a ceiling on what its steps may be. */
export type TaskAutonomy = "fixed" | "self_healing" | "proactive" | "autonomous";

export interface Workflow {
  /** 2 may hold agent steps. */
  version: 1 | 2;
  inputs: WorkflowInput[];
  steps: WorkflowStep[];
  /** Null or absent: the lowest level its steps need. */
  autonomy?: TaskAutonomy | null;
  /** Run when a step fails and the run stops, not when a person said no. Absent: none. */
  after_failure?: WorkflowStep[];
  /** What the task keeps between runs (decision 0034). Absent: nothing. */
  memory?: MemoryEntry[];
}

/** GET /api/scheduled-tasks/{id}/memory: by name, the value kept, when, and by which run ("you"
 * for a person's edit). */
export type TaskMemoryValues = Record<string, { value: unknown; at: string; by: string }>;

/** GET /api/scheduled-tasks/{id}/runs/{run}/report */
export interface RunReport {
  autonomy: TaskAutonomy;
  loops: { step_id: string; title: string; done: number; total: number; skipped?: number }[];
  not_done: { step_id: string; title: string; iteration: number[]; status: string; error: string | null }[];
  assumed: { step_id: string; title: string; iteration: number[]; values: string[] }[];
  unanswered: { step_id: string; title: string; iteration: number[] }[];
  healed: { step_id: string; title: string; iteration: number[]; error: string; did: string; carried?: boolean }[];
  irreversible: { step_id: string; title: string; iteration: number[] }[];
  /** Failures that didn't stop the run (decision 0032). Absent on older servers. */
  recovered?: {
    step_id: string;
    title: string;
    iteration: number[];
    how: "skipped" | "fallback" | "item_skipped";
    error: string | null;
  }[];
  retried?: { step_id: string; title: string; iteration: number[]; attempts: number; worked: boolean }[];
  /** The steps that ran because the run failed. */
  after_failure?: { step_id: string; title: string; iteration: number[]; status: string; error: string | null }[];
  /** What the run keeps for the next one, kept only if it finished (decision 0034). */
  remembered?: { step_id: string; title: string; name: string; label?: string; value: unknown }[];
  /** The check that ended the run with nothing to do. */
  ended?: { step_id: string; title: string } | null;
  tool_calls: number;
  tokens: number;
  cached_tokens: number;
  seconds: number | null;
  fixes: HealFixes;
}

/** The revision a run's heals propose (decision 0030): saved arguments to replace, and the heals
 * that changed more than that. */
export interface HealFixes {
  fixes: { step_id: string; title: string; name: string; was: string; now: string }[];
  workflow: Workflow | null;
  left: { step_id: string; title: string; did: string }[];
}

export type StepRecord = WorkflowStepRecord;
export type StepStatus = StepRecord["status"];
export type CheckResult = WorkflowCheck;
