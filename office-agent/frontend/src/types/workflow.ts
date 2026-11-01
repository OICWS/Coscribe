// Mirrors src/coscribe/workflow_spec/spec.py (the definition) and
// engine.py's StepRecord (one step of one run), which comes from wire.gen.ts.

import type { WorkflowCheck, WorkflowStepRecord } from "./wire.gen";

export type StepKind = "tool" | "script" | "llm" | "agent" | "check" | "approval" | "branch" | "choice" | "loop";
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

export interface ToolStep extends StepBase {
  kind: "tool";
  tool: string;
  args: Record<string, unknown>;
  save_as: string | null;
  /** Sends, submits, pays or deletes outside this machine: a test stops before it. */
  irreversible: boolean;
}

export interface ScriptStep extends StepBase {
  kind: "script";
  code: string;
  inputs: Record<string, unknown>;
  save_as: string | null;
}

export interface LLMStep extends StepBase {
  kind: "llm";
  prompt: string;
  fields: OutputField[];
  model: string | null;
  save_as: string;
}

/** Decision 0028. "bounded" may use only `tools`, `folders` and `sites`. */
export interface AgentStep extends StepBase {
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
}

export interface ApprovalStep extends StepBase {
  kind: "approval";
  message: string;
  /** Empty: always pause. */
  when: Condition[];
  /** Absent: all. */
  match?: Match;
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
}

export type WorkflowStep =
  | ToolStep
  | ScriptStep
  | LLMStep
  | AgentStep
  | CheckStep
  | ApprovalStep
  | BranchStep
  | ChoiceStep
  | LoopStep;
export type BlockStep = BranchStep | ChoiceStep | LoopStep;

/** Decision 0030: one switch per task, a ceiling on what its steps may be. */
export type TaskAutonomy = "fixed" | "self_healing" | "proactive" | "autonomous";

export interface Workflow {
  /** 2 may hold agent steps. */
  version: 1 | 2;
  inputs: WorkflowInput[];
  steps: WorkflowStep[];
  /** Null or absent: the lowest level its steps need. */
  autonomy?: TaskAutonomy | null;
}

/** GET /api/scheduled-tasks/{id}/runs/{run}/report */
export interface RunReport {
  autonomy: TaskAutonomy;
  loops: { step_id: string; title: string; done: number; total: number }[];
  not_done: { step_id: string; title: string; iteration: number[]; status: string; error: string | null }[];
  assumed: { step_id: string; title: string; iteration: number[]; values: string[] }[];
  healed: { step_id: string; title: string; iteration: number[]; error: string; did: string; carried?: boolean }[];
  irreversible: { step_id: string; title: string; iteration: number[] }[];
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
