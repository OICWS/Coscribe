import type { OnFailure, RecoveringStep, WorkflowStep } from "../types/workflow";
import type { QuickField } from "./quickEdit";
import { canRecover } from "./workflowTree";

// What a step does when it fails (decision 0032), in plain words and as quick-edit fields.

/** A step without its own setting: stop the run at once (workflow_spec's OnFailure defaults). */
export const NO_FAILURE: OnFailure = { retries: 0, wait_seconds: 30, then: "stop", steps: [] };

/** `step` with its failure setting changed; one that only stops is stored as no setting. */
export function withFailure<T extends RecoveringStep>(step: T, change: Partial<OnFailure>): T {
  const next = { ...NO_FAILURE, ...step.on_failure, ...change };
  const plain = next.retries === 0 && next.then === "stop" && next.steps.length === 0;
  return { ...step, on_failure: plain ? null : next };
}

export function waitWords(seconds: number): string {
  if (seconds % 60 === 0 && seconds > 0) return seconds === 60 ? "1 minute" : `${seconds / 60} minutes`;
  return seconds === 1 ? "1 second" : `${seconds} seconds`;
}

function tries(retries: number): string {
  return retries === 1 ? "1 more try" : `${retries} more tries`;
}

function steps(count: number): string {
  return count === 1 ? "1 other step" : `${count} other steps`;
}

/** One line for a step's card, or null when a failure simply stops the run. */
export function failureLine(step: WorkflowStep): string | null {
  if (!canRecover(step) || !step.on_failure) return null;
  const { retries, then, steps: inPlace } = step.on_failure;
  const after =
    then === "skip" ? "skip it" : then === "steps" ? `run ${steps(inPlace.length)}` : retries > 0 ? "stop" : null;
  if (retries === 0) return after ? `If it fails: ${after}` : null;
  return `If it fails: ${tries(retries)}${after && after !== "stop" ? `, then ${after}` : ""}`;
}

const RETRY_OPTIONS = [0, 1, 2, 3, 4, 5].map((n) => ({
  value: n,
  label: n === 0 ? "No" : n === 1 ? "Once" : `Up to ${n} times`,
}));

function waitOptions(current: number) {
  const usual = [5, 10, 30, 60, 120, 300];
  const all = usual.includes(current) ? usual : [...usual, current].sort((a, b) => a - b);
  return all.map((seconds) => ({ value: seconds, label: waitWords(seconds) }));
}

/** The quick edit's fields for what a step does when it fails. Running other steps in its place
 * changes the workflow's shape, so it is shown here and set in the full editor. */
export function failureFields(step: RecoveringStep): QuickField[] {
  const failure = { ...NO_FAILURE, ...step.on_failure };
  const section = "If it fails";
  const fields: QuickField[] = [];
  if ("irreversible" in step && step.irreversible) {
    fields.push({
      key: "failure:retries",
      label: "Try again",
      kind: "shown",
      value: "Never. It can’t be undone, so it isn’t done twice.",
      section,
    });
  } else {
    fields.push({
      key: "failure:retries",
      label: "Try again",
      kind: "pick",
      value: failure.retries,
      options: RETRY_OPTIONS,
      hint: "For a site or service that sometimes doesn’t answer",
      section,
    });
  }
  if (failure.retries > 0) {
    fields.push({
      key: "failure:wait_seconds",
      label: "Wait between tries",
      kind: "pick",
      value: failure.wait_seconds,
      options: waitOptions(failure.wait_seconds),
    });
  }
  const label = failure.retries > 0 ? "If it still fails" : "Then";
  if (failure.then === "steps") {
    const count = failure.steps.length;
    fields.push({
      key: "failure:then",
      label,
      kind: "shown",
      value: `Run ${steps(count)} in its place. Change them in the full editor.`,
    });
  } else {
    fields.push({
      key: "failure:then",
      label,
      kind: "pick",
      value: failure.then,
      options: [
        { value: "stop", label: "Stop the run" },
        { value: "skip", label: "Skip it and go on" },
      ],
      hint: failure.then === "skip" ? "The report lists it as skipped." : undefined,
    });
  }
  return fields;
}
