import { NO_FAILURE, waitWords, withFailure } from "../../lib/failureWords";
import type { LoopStep, OnFailure, RecoveringStep } from "../../types/workflow";
import { FieldLabel } from "./fields";
import { SelectMenu } from "../SelectMenu";

// What a step does when it fails (decision 0032), in the full editor. The steps that run in its
// place are a list under the step's card, edited like a branch's.

const THEN: [OnFailure["then"], string][] = [
  ["stop", "Stop the run"],
  ["skip", "Skip it and go on"],
  ["steps", "Run other steps instead"],
];

const THEN_HINT: Record<OnFailure["then"], string> = {
  stop: "The run stops here and counts as failed.",
  skip: "The run goes on without its result, so later steps can’t use it. The report lists it as skipped.",
  steps:
    "Add them under If it fails below. They can read {{failure.step}} and {{failure.message}}; give one the same result name for later steps to use either.",
};

const WAITS = [5, 10, 30, 60, 120, 300];

function Choices<V extends string>({
  label,
  options,
  value,
  onPick,
}: {
  label: string;
  options: [V, string][];
  value: V;
  onPick: (value: V) => void;
}) {
  return (
    <div role="radiogroup" aria-label={label} className="flex flex-wrap gap-1 text-[13px]">
      {options.map(([option, text]) => (
        <button
          key={option}
          type="button"
          role="radio"
          aria-checked={value === option}
          className={`rounded-md px-2.5 py-1 ${
            value === option
              ? "bg-[var(--card-bg)] font-medium text-[var(--fg)]"
              : "text-[var(--muted)] hover:text-[var(--fg)]"
          }`}
          onClick={() => onPick(option)}
        >
          {text}
        </button>
      ))}
    </div>
  );
}

export function FailureEditor<T extends RecoveringStep>({ step, onChange }: { step: T; onChange: (step: T) => void }) {
  const failure = { ...NO_FAILURE, ...step.on_failure };
  const final = "irreversible" in step && step.irreversible;
  const set = (change: Partial<OnFailure>) => onChange(withFailure(step, change));
  const waits = WAITS.includes(failure.wait_seconds) ? WAITS : [...WAITS, failure.wait_seconds].sort((a, b) => a - b);
  return (
    <fieldset className="flex flex-col gap-2 border-t border-[var(--border)] pt-3">
      <legend className="sr-only">If it fails</legend>
      <span className="text-[13px] font-medium">If it fails</span>
      <div className="flex flex-wrap items-end gap-3">
        <div>
          <FieldLabel htmlFor={`${step.id}-retries`}>Try again</FieldLabel>
          <SelectMenu
            id={`${step.id}-retries`}
            variant="field"
            className="w-40"
            disabled={final}
            value={final ? 0 : failure.retries}
            options={[0, 1, 2, 3, 4, 5].map((n) => ({
              value: n,
              label: n === 0 ? (final ? "Never" : "No") : n === 1 ? "Once" : `Up to ${n} times`,
            }))}
            onChange={(retries) => set({ retries })}
          />
        </div>
        {failure.retries > 0 && (
          <div>
            <FieldLabel htmlFor={`${step.id}-wait`}>Wait between tries</FieldLabel>
            <SelectMenu
              id={`${step.id}-wait`}
              variant="field"
              className="w-36"
              value={failure.wait_seconds}
              options={waits.map((seconds) => ({ value: seconds, label: waitWords(seconds) }))}
              onChange={(wait_seconds) => set({ wait_seconds })}
            />
          </div>
        )}
      </div>
      {final && (
        <p className="text-xs text-[var(--muted)]">It can’t be undone, so it is never tried twice on its own.</p>
      )}
      <span className="mt-1 text-xs text-[var(--muted)]">{failure.retries > 0 ? "If it still fails" : "Then"}</span>
      <Choices
        label={`${step.title}: if it fails`}
        options={THEN}
        value={failure.then}
        onPick={(then) => set({ then, steps: then === "steps" ? failure.steps : [] })}
      />
      <p className="text-xs text-[var(--muted)]">{THEN_HINT[failure.then]}</p>
    </fieldset>
  );
}

export function ItemFailureEditor({ step, onChange }: { step: LoopStep; onChange: (step: LoopStep) => void }) {
  return (
    <div className="flex flex-col gap-1.5">
      <span className="text-[13px] font-medium">If one item fails</span>
      <Choices
        label={`${step.title}: if one item fails`}
        options={[
          ["stop", "Stop the run"],
          ["skip", "Skip that item and go on"],
        ]}
        value={step.on_item_failure ?? "stop"}
        onPick={(value) => onChange({ ...step, on_item_failure: value })}
      />
      {step.on_item_failure === "skip" && (
        <p className="text-xs text-[var(--muted)]">
          The report lists each skipped item and why. When every item fails, the run fails.
        </p>
      )}
    </div>
  );
}
