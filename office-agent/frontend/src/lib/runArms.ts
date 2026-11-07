import type { StepRecord, WorkflowStep } from "../types/workflow";
import { KIND_COLOR } from "./workflowLabels";
import { canRecover } from "./workflowTree";

interface RunArm {
  arm: string;
  label: string;
  steps: WorkflowStep[];
  color: string;
}

/** The lists a step holds in a run's view, and which of them ran. */
interface RunArms {
  arms: RunArm[];
  taken: string[];
  /** What a list that didn't run says. */
  idle: string;
}

function fallbackArm(step: WorkflowStep, record: StepRecord | undefined): RunArms | null {
  if (!canRecover(step) || step.on_failure?.then !== "steps") return null;
  const ran = record?.recovered === "fallback";
  return {
    arms: [{ arm: "fallback", label: "If it fails", steps: step.on_failure.steps, color: "var(--warning)" }],
    taken: ran ? ["fallback"] : [],
    idle: record?.status === "done" ? "not needed" : "only if it fails",
  };
}

/** The lists under a branch, a choice, a parallel step or a step with steps in its place, by the
 * record's arm. Every lane of a parallel step runs once it has started (decision 0036). */
export function runArms(step: WorkflowStep, record: StepRecord | undefined): RunArms | null {
  const arm = (record?.output as { arm?: string } | null | undefined)?.arm ?? null;
  const decided = record?.status === "done" && arm ? [arm] : [];
  const idle = decided.length > 0 ? "not taken" : "not decided yet";
  if (step.kind === "branch") {
    const color = KIND_COLOR.branch;
    const arms = [
      { arm: "then", label: "Then", steps: step.then, color },
      { arm: "otherwise", label: "Otherwise", steps: step.otherwise, color },
    ];
    return { arms, taken: decided, idle };
  }
  if (step.kind === "choice") {
    const color = KIND_COLOR.choice;
    const arms = [
      ...step.cases.map((c, index) => ({ arm: `case:${index}`, label: `Is “${c.is}”`, steps: c.steps, color })),
      { arm: "otherwise", label: "Anything else", steps: step.otherwise, color },
    ];
    return { arms, taken: decided, idle };
  }
  const fallback = fallbackArm(step, record);
  if (step.kind !== "parallel") return fallback;
  const color = KIND_COLOR.parallel;
  const lanes = step.lanes.map((lane, index) => ({
    arm: `lane:${index}`,
    label: lane.label,
    steps: lane.steps,
    color,
  }));
  const started = record !== undefined && record.status !== "skipped";
  return {
    arms: [...lanes, ...(fallback?.arms ?? [])],
    taken: [...(started ? lanes.map((lane) => lane.arm) : []), ...(fallback?.taken ?? [])],
    idle: started ? (fallback?.idle ?? "") : "not started",
  };
}
