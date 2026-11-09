import { MAX_PER_HOUR, type ScheduleForm } from "../lib/scheduleForm";
import { matchingField } from "../lib/itemFields";
import type { WorkflowInput } from "../types/workflow";
import { SelectMenu } from "./SelectMenu";

// What fills a workflow's inputs when something from outside starts a run: a connector's new item
// (decision 0039) or an event a program sends (decision 0040). Each input takes a field of it, the
// whole of it, or its own default; and the most runs such things may start in an hour.

const control = "rounded-md border border-[var(--border)] bg-transparent px-2 py-1.5 text-sm outline-none";
const WHOLE_ITEM = "*";

function sample(value: unknown): string {
  const text = typeof value === "string" ? value : JSON.stringify(value);
  return text.length > 40 ? `${text.slice(0, 39)}…` : text;
}

export function InputsFromItem({
  what = "new item",
  inputs,
  fields,
  form,
  onChange,
}: {
  /** What starts a run, as the label says it: "new item", "event". */
  what?: string;
  inputs: WorkflowInput[];
  fields: Record<string, unknown>;
  form: ScheduleForm;
  onChange: (form: ScheduleForm) => void;
}) {
  const paths = Object.keys(fields);
  const saved = Object.values(form.inputsFrom).filter((path) => path && path !== WHOLE_ITEM && !(path in fields));
  const options = [
    { value: "", label: "Its default" },
    { value: WHOLE_ITEM, label: "The whole item" },
    ...[...paths, ...saved].map((path) => ({
      value: path,
      label: path in fields ? `${path} · ${sample(fields[path])}` : path,
    })),
  ];
  return (
    <div className="flex flex-col gap-1.5">
      <span className="text-sm text-[var(--muted)]">Each {what} fills in</span>
      <div className="grid grid-cols-[minmax(0,140px)_minmax(0,1fr)] items-center gap-x-3 gap-y-1.5">
        {inputs.map((input) => (
          <div key={input.name} className="contents">
            <span className="truncate text-sm">{input.label || input.name}</span>
            <SelectMenu
              ariaLabel={`${input.label || input.name} from`}
              variant="field"
              value={form.inputsFrom[input.name] ?? matchingField(input, paths)}
              options={options}
              onChange={(path) => onChange({ ...form, inputsFrom: { ...form.inputsFrom, [input.name]: path } })}
            />
          </div>
        ))}
      </div>
    </div>
  );
}

export function PerHour({ form, onChange }: { form: ScheduleForm; onChange: (form: ScheduleForm) => void }) {
  return (
    <>
      <span className="text-[var(--muted)]">At most</span>
      <input
        aria-label="Runs an hour at most"
        type="number"
        min={1}
        max={MAX_PER_HOUR}
        className={`${control} w-16`}
        value={form.perHour}
        onChange={(e) =>
          onChange({ ...form, perHour: Math.max(1, Math.min(MAX_PER_HOUR, Number(e.target.value) || 1)) })
        }
      />
      <span className="text-[var(--muted)]">runs an hour</span>
    </>
  );
}
