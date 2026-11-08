import { inputClass } from "../../lib/formStyles";
import type { ParallelStep } from "../../types/workflow";
import type { EditorProps } from "./editorParts";
import { AddRowButton, FieldLabel, RemoveButton } from "./fields";

/** workflow_spec's MAX_LANES. */
const MAX_LANES = 6;

/** The lanes of a step that runs them at the same time (decision 0036): their names, and adding
 * or taking one out. Their steps are edited in their own lists under the step. */
export function ParallelEditor({ step, onChange }: EditorProps<ParallelStep>) {
  const rename = (index: number, label: string) =>
    onChange({ ...step, lanes: step.lanes.map((lane, i) => (i === index ? { ...lane, label } : lane)) });
  const taken = (index: number) =>
    step.lanes.some(
      (lane, i) => i !== index && lane.label.trim().toLowerCase() === step.lanes[index].label.trim().toLowerCase(),
    );
  return (
    <div className="flex flex-col gap-2">
      <FieldLabel hint="They run at the same time; the run goes on once every lane has ended">Lanes</FieldLabel>
      {step.lanes.map((lane, index) => (
        <div key={index} className="flex items-center gap-2">
          <span className="w-14 shrink-0 text-[13px] text-[var(--muted)]">Lane {index + 1}</span>
          <input
            aria-label={`Lane ${index + 1} name`}
            aria-invalid={!lane.label.trim() || taken(index)}
            maxLength={60}
            className={`${inputClass} min-w-0 flex-1`}
            value={lane.label}
            onChange={(e) => rename(index, e.target.value)}
          />
          {lane.steps.length > 0 || step.lanes.length <= 2 ? (
            <span className="w-16 shrink-0 text-right text-xs text-[var(--muted)]">
              {lane.steps.length === 1 ? "1 step" : `${lane.steps.length} steps`}
            </span>
          ) : (
            <RemoveButton
              label={`Remove lane ${index + 1}`}
              onClick={() => onChange({ ...step, lanes: step.lanes.filter((_, i) => i !== index) })}
            />
          )}
        </div>
      ))}
      {step.lanes.length < MAX_LANES && (
        <AddRowButton
          onClick={() =>
            onChange({ ...step, lanes: [...step.lanes, { label: `Lane ${step.lanes.length + 1}`, steps: [] }] })
          }
        >
          Add a lane
        </AddRowButton>
      )}
      <p className="text-xs text-[var(--muted)]">
        A lane reads only what came before this step, never another lane's results; after it, every lane's results can
        be read. An empty lane can be taken out.
      </p>
    </div>
  );
}
